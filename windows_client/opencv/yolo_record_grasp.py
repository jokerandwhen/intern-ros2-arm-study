"""
YOLO检测 + 手动示教录制 + 回放

工作流程:
  1. YOLO实时检测物体，画面显示检测框
  2. 检测到物体后，按 R 开始录制
  3. 禁用扭矩，你手动移动从动臂完成抓取动作
  4. 按 E 停止录制
  5. 按 P 回放录制的动作（使能扭矩，机械臂自动复刻）
  6. 可以反复回放，也可以录制多个任务

用法:
  python yolo_record_grasp.py                # 默认摄像头0
  python yolo_record_grasp.py 0 --conf 0.5   # 调整置信度
  python yolo_record_grasp.py 0 --class cup   # 只检测cup

按键说明:
  空格   - 开始/暂停YOLO检测（暂停后可手动移动臂调整位置）
  R     - 开始录制（禁用扭矩，你可以手动移动从动臂）
  E     - 停止录制
  P     - 回放录制的动作
  L     - 列出所有已录制的任务
  H     - 回到home位置
  Q/Esc - 退出
"""
import cv2
import sys
import os
import time
import json
import argparse
import threading
import numpy as np
import torch
import msvcrt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "grap001"))

from ultralytics import YOLO
from arm_controller import SoArmController

# ============================================================
#  常量
# ============================================================
COCO_CLASSES = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
    'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
    'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
    'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
    'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
    'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
    'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
    'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
    'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
    'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
    'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear',
    'hair drier', 'toothbrush'
]

GRASPABLE = {'bottle', 'cup', 'apple', 'banana', 'orange', 'book', 'cell phone',
             'scissors', 'fork', 'knife', 'spoon', 'bowl', 'remote', 'teddy bear',
             'sports ball', 'vase'}

COLORS = np.random.randint(50, 255, size=(80, 3), dtype=np.uint8)

POSITIONS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "grap001", "positions.json"
)

RECORDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "records")
RECORD_FREQ = 20  # 录制频率 Hz


# ============================================================
#  ThreadedCamera
# ============================================================
class ThreadedCamera:
    def __init__(self, cam_id=0, width=640, height=480):
        self.cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.ret = False
        self.frame = None
        self._running = True
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self):
        while self._running:
            ret, frame = self.cap.read()
            if ret:
                with self._lock:
                    self.ret = True
                    self.frame = frame
            else:
                time.sleep(0.005)

    def read(self):
        with self._lock:
            if self.frame is not None:
                return True, self.frame.copy()
            return False, None

    def isOpened(self):
        return self.cap.isOpened()

    def release(self):
        self._running = False
        self._thread.join(timeout=1.0)
        self.cap.release()


# ============================================================
#  工具函数
# ============================================================
def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {name: {int(k): v for k, v in pos.items()} for name, pos in data.items()}
    return {}

def ensure_records_dir():
    if not os.path.exists(RECORDS_DIR):
        os.makedirs(RECORDS_DIR)

def get_record_path(name):
    return os.path.join(RECORDS_DIR, f"{name}.json")

def list_records():
    ensure_records_dir()
    files = [f[:-5] for f in os.listdir(RECORDS_DIR) if f.endswith('.json')]
    return sorted(files)

def detect_objects(model, frame, conf_threshold=0.4, target_classes=None, device='cpu'):
    results = model(frame, conf=conf_threshold, verbose=False, imgsz=640, device=device)
    detections = []
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = COCO_CLASSES[cls_id]
            if target_classes and cls_name not in target_classes:
                continue
            detections.append({
                'bbox': (x1, y1, x2, y2),
                'conf': conf,
                'class': cls_name,
                'cls_id': cls_id,
                'center': ((x1+x2)//2, (y1+y2)//2),
                'area': (x2-x1) * (y2-y1),
            })
    return detections

def draw_detections(frame, detections):
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        cls_name = det['class']
        conf = det['conf']
        cls_id = det['cls_id']
        color = COLORS[cls_id].tolist()
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"{cls_name} {conf:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
        cv2.putText(frame, label, (x1, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cx, cy = det['center']
        cv2.circle(frame, (cx, cy), 4, color, -1)
        if cls_name in GRASPABLE:
            cv2.putText(frame, "GRASP", (x1, y2 + 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    return frame


# ============================================================
#  录制功能
# ============================================================
def start_recording(arm, cam, task_name):
    """录制模式：禁用扭矩，用户手动移动从动臂，实时记录关节位置"""
    print("\n" + "=" * 60)
    print(f"开始录制: {task_name}")
    print("=" * 60)
    
    # 禁用扭矩
    print("禁用扭矩，你可以手动移动从动臂...")
    arm.disable_torque()
    time.sleep(0.5)
    
    # 读取当前位置
    start_pos = arm.read_all_positions_fast()
    print(f"起始位置: {start_pos}")
    
    print(f"\n录制频率: {RECORD_FREQ} Hz")
    print("\n操作说明:")
    print("  1. 手动移动从动臂完成抓取动作")
    print("  2. 摄像头画面会持续显示")
    print("  3. 完成后按【E】停止录制")
    print("  4. 按【Q】取消录制")
    print()
    
    frames = []
    start_time = time.time()
    frame_interval = 1.0 / RECORD_FREQ
    
    print("录制中... (按 E 停止, Q 取消)")
    print(f"{'时间':>6}s  {'帧数':>5}  shoulder  lift   elbow  wrist_f wrist_r gripper")
    print("-" * 75)
    
    recording = True
    cancelled = False
    
    while recording:
        # 检查键盘
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'e' or key == b'E':
                recording = False
            elif key == b'q' or key == b'Q' or key == b'\x1b':
                recording = False
                cancelled = True
        
        # 读取摄像头画面并显示（保持画面刷新）
        ret, frame = cam.read()
        if ret and frame is not None:
            h, w = frame.shape[:2]
            # 画中心十字
            cv2.line(frame, (w//2-15, h//2), (w//2+15, h//2), (0, 255, 0), 1)
            cv2.line(frame, (w//2, h//2-15), (w//2, h//2+15), (0, 255, 0), 1)
            # 录制状态
            elapsed = time.time() - start_time
            cv2.putText(frame, f"RECORDING: {task_name}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            cv2.putText(frame, f"Time: {elapsed:.1f}s  Frames: {len(frames)}", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(frame, "Press [E] to stop, [Q] to cancel", (10, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.imshow("YOLO Record Grasp", frame)
            cv2.waitKey(1)
        
        # 读取关节位置
        current_time = time.time()
        elapsed = current_time - start_time
        
        pos = arm.read_all_positions_fast()
        frames.append({
            't': round(elapsed, 4),
            'pos': {str(k): v for k, v in pos.items()}
        })
        
        # 打印进度
        if len(frames) % 20 == 1:
            print(f"{elapsed:6.2f}s  {len(frames):5d}  "
                  f"{pos[1]:7d}  {pos[2]:5d}  {pos[3]:5d}  "
                  f"{pos[4]:6d}  {pos[5]:6d}  {pos[6]:6d}")
        
        # 等待下一帧
        next_frame_time = start_time + len(frames) * frame_interval
        sleep_time = next_frame_time - time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)
    
    duration = time.time() - start_time
    print("-" * 75)
    
    if cancelled or len(frames) < 5:
        print(f"\n录制已取消")
        # 重新使能扭矩
        arm.enable_torque()
        time.sleep(0.3)
        return None
    
    print(f"\n录制完成!")
    print(f"  总时长: {duration:.2f}s")
    print(f"  总帧数: {len(frames)}")
    print(f"  实际频率: {len(frames)/duration:.1f} Hz")
    
    # 保存录制数据
    ensure_records_dir()
    record_data = {
        'name': task_name,
        'freq': RECORD_FREQ,
        'duration': round(duration, 2),
        'frames': len(frames),
        'start_pos': {str(k): v for k, v in start_pos.items()},
        'data': frames
    }
    
    path = get_record_path(task_name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(record_data, f, indent=2)
    print(f"  已保存到: {path}")
    
    # 重新使能扭矩
    arm.enable_torque()
    time.sleep(0.3)
    
    return record_data


# ============================================================
#  回放功能
# ============================================================
def replay_recording(arm, cam, task_name):
    """回放录制的动作"""
    path = get_record_path(task_name)
    if not os.path.exists(path):
        print(f"\n录制 '{task_name}' 不存在")
        available = list_records()
        if available:
            print(f"可用录制: {', '.join(available)}")
        else:
            print("暂无录制")
        return False
    
    with open(path, 'r', encoding='utf-8') as f:
        record_data = json.load(f)
    
    frames = record_data['data']
    duration = record_data['duration']
    
    print("\n" + "=" * 60)
    print(f"回放: {task_name}")
    print("=" * 60)
    print(f"  录制时长: {duration}s")
    print(f"  帧数: {len(frames)}")
    
    # 显示第一帧
    first_frame = frames[0]
    start_pos = {int(k): v for k, v in first_frame['pos'].items()}
    print(f"  起始位置: {start_pos}")
    
    print("\n操作说明:")
    print("  按 Enter 开始回放")
    print("  按 Ctrl+C 可随时停止")
    
    # 等待用户确认，同时保持画面刷新
    print("\n准备好后按 Enter 开始回放...")
    waiting = True
    while waiting:
        ret, frame = cam.read()
        if ret and frame is not None:
            h, w = frame.shape[:2]
            cv2.putText(frame, f"Replay: {task_name}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(frame, f"Duration: {duration}s  Frames: {len(frames)}", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(frame, "Press [Enter] to start", (10, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.imshow("YOLO Record Grasp", frame)
        
        key = cv2.waitKey(30) & 0xFF
        if key == ord('\r') or key == 13:  # Enter
            waiting = False
        elif key == ord('q') or key == 27:
            print("已取消回放")
            return False
    
    # 使能扭矩
    print("使能扭矩...")
    arm.enable_torque()
    time.sleep(0.5)
    
    # 先平滑移动到起始位置
    print("移动到起始位置...")
    arm.move_smooth(start_pos, steps=20, delay=0.03)
    time.sleep(0.3)
    
    print("\n回放中...")
    print(f"{'时间':>6}s  {'帧':>5}/{len(frames)}  shoulder  lift   elbow  wrist_f wrist_r gripper")
    print("-" * 75)
    
    frame_interval = 1.0 / RECORD_FREQ
    start_time = time.time()
    
    try:
        for i, frame in enumerate(frames):
            target = {int(k): v for k, v in frame['pos'].items()}
            arm._sync_write_positions(target)
            
            # 同时显示摄像头画面
            ret, cam_frame = cam.read()
            if ret and cam_frame is not None:
                h, w = cam_frame.shape[:2]
                elapsed = time.time() - start_time
                cv2.putText(cam_frame, f"REPLAY: {task_name}", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(cam_frame, f"Time: {elapsed:.1f}s  Frame: {i+1}/{len(frames)}", (10, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                cv2.imshow("YOLO Record Grasp", cam_frame)
                cv2.waitKey(1)
            
            elapsed = time.time() - start_time
            if (i + 1) % 20 == 0 or i == 0 or i == len(frames) - 1:
                print(f"{elapsed:6.2f}s  {i+1:5d}/{len(frames)}  "
                      f"{target[1]:7d}  {target[2]:5d}  {target[3]:5d}  "
                      f"{target[4]:6d}  {target[5]:6d}  {target[6]:6d}")
            
            # 等待下一帧时间
            expected_time = (i + 1) * frame_interval
            actual_time = time.time() - start_time
            sleep_time = expected_time - actual_time
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        actual_duration = time.time() - start_time
        print("-" * 75)
        print(f"\n回放完成! 实际时长: {actual_duration:.2f}s")
        return True
        
    except KeyboardInterrupt:
        print("\n\n回放被中断")
        return False
    finally:
        # 不停用扭矩，保持就绪状态
        pass


# ============================================================
#  主程序
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="YOLO检测 + 手动示教录制 + 回放")
    parser.add_argument("cam", type=int, nargs="?", default=0, help="摄像头编号")
    parser.add_argument("--conf", type=float, default=0.4, help="置信度阈值")
    parser.add_argument("--class", dest="classes", nargs="*", help="只检测指定类别")
    args = parser.parse_args()

    target_classes = set(args.classes) if args.classes else None

    print("=" * 60)
    print("YOLO检测 + 手动示教录制 + 回放")
    print("=" * 60)

    # 加载home位置
    positions = load_json(POSITIONS_FILE)
    if 'home' not in positions:
        print("\n缺少 home 位置，请先在grap001中设置positions.json")
        return

    print(f"\n摄像头: {args.cam}（夹爪摄像头）")
    print(f"置信度: {args.conf}")
    print(f"目标物体: {', '.join(target_classes) if target_classes else '全部可抓取物体'}")

    # 打开摄像头
    print("\n打开摄像头...")
    cam = ThreadedCamera(args.cam, 640, 480)
    if not cam.isOpened():
        print("无法打开摄像头")
        return

    # 等摄像头就绪
    time.sleep(0.5)

    # 加载模型
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"加载YOLOv8模型 (device={device})...")
    model = YOLO('yolov8n.pt')
    print(f"✓ 模型已加载，使用 {'GPU: ' + torch.cuda.get_device_name(0) if device == 'cuda' else 'CPU'}")

    # 预热
    print("预热YOLO模型...")
    ret, frame = cam.read()
    if ret:
        model(frame, conf=args.conf, verbose=False, imgsz=640, device=device)
    print("✓ 预热完成")

    # 连接机械臂
    print("连接机械臂...")
    arm = SoArmController(port="COM3")
    arm.connect()
    time.sleep(0.3)
    arm.enable_torque()
    time.sleep(0.3)

    # 移动到home
    print("移动到home...")
    arm.move_smooth(positions['home'], steps=20, delay=0.03)
    time.sleep(0.5)

    print("\n" + "=" * 60)
    print("系统已启动！")
    print("=" * 60)
    print("  空格   - 暂停/恢复YOLO检测")
    print("  R     - 开始录制（禁用扭矩，手动移动从动臂）")
    print("  E     - 停止录制")
    print("  P     - 回放录制的动作")
    print("  L     - 列出所有录制")
    print("  H     - 回到home位置")
    print("  Q/Esc - 退出")
    print("=" * 60)

    # 状态
    detecting = True  # 是否正在检测
    recording = False
    current_task = None
    task_counter = 1
    frame_count = 0
    last_detections = []
    DETECT_INTERVAL = 5

    fps_timer = time.time()
    fps_count = 0
    current_fps = 0

    # 主循环
    while True:
        ret, frame = cam.read()
        if not ret:
            time.sleep(0.01)
            continue

        frame_count += 1
        fps_count += 1

        # YOLO检测（只在检测模式下）
        if detecting and frame_count % DETECT_INTERVAL == 0:
            detections = detect_objects(model, frame, args.conf, target_classes, device)
            if not target_classes:
                detections = [d for d in detections if d['class'] in GRASPABLE]
            last_detections = detections

        # 画检测框
        frame = draw_detections(frame, last_detections)

        # 中心十字
        h, w = frame.shape[:2]
        cv2.line(frame, (w//2-15, h//2), (w//2+15, h//2), (0, 255, 0), 1)
        cv2.line(frame, (w//2, h//2-15), (w//2, h//2+15), (0, 255, 0), 1)

        # FPS计算
        if time.time() - fps_timer >= 1.0:
            current_fps = fps_count
            fps_count = 0
            fps_timer = time.time()

        # 状态信息
        status = "DETECTING" if detecting else "PAUSED"
        obj_count = len(last_detections)
        info = f"FPS:{current_fps} {status} Obj:{obj_count} {device.upper()}"
        cv2.putText(frame, info, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # 检测到物体提示
        if detecting and obj_count > 0:
            cv2.putText(frame, "Press [R] to record grasp", (10, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.imshow("YOLO Record Grasp", frame)

        # 键盘处理
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord(' '):
            # 暂停/恢复检测
            detecting = not detecting
            if detecting:
                print("\n恢复YOLO检测")
            else:
                print("\n暂停YOLO检测（你可以移动物体位置）")
        elif key == ord('r') or key == ord('R'):
            # 开始录制
            task_name = f"grasp_{task_counter:03d}"
            print(f"\n准备录制: {task_name}")
            print("按 Enter 开始录制（将禁用扭矩）...")
            
            # 等待确认
            while True:
                k = cv2.waitKey(30) & 0xFF
                if k == ord('\r') or k == 13:
                    break
                elif k == ord('q') or k == 27:
                    print("已取消")
                    break
                # 保持画面刷新
                ret2, frame2 = cam.read()
                if ret2 and frame2 is not None:
                    cv2.putText(frame2, "Press [Enter] to start recording", (60, 240),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    cv2.imshow("YOLO Record Grasp", frame2)
            else:
                continue
            
            # 开始录制
            result = start_recording(arm, cam, task_name)
            if result:
                task_counter += 1
                print(f"\n✓ 录制已保存，按 P 可以回放")
        
        elif key == ord('p') or key == ord('P'):
            # 回放最新的录制
            available = list_records()
            if not available:
                print("\n暂无录制，请先按 R 录制")
            else:
                # 回放最新的
                latest = available[-1]
                print(f"\n回放最新录制: {latest}")
                replay_recording(arm, cam, latest)
        
        elif key == ord('l') or key == ord('L'):
            # 列出所有录制
            available = list_records()
            print("\n已录制的任务:")
            if available:
                for name in available:
                    path = get_record_path(name)
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"  {name:<20} {data['duration']}s  {data['frames']}帧")
            else:
                print("  (暂无)")
        
        elif key == ord('h') or key == ord('H'):
            # 回home
            print("\n回到home...")
            arm.move_smooth(positions['home'], steps=20, delay=0.03)
            time.sleep(0.3)

    # 退出
    cam.release()
    cv2.destroyAllWindows()
    print("\n回到home...")
    arm.move_smooth(positions['home'], steps=20, delay=0.03)
    time.sleep(0.3)
    arm.disable_torque()
    arm.disconnect()
    print(f"\n完成! 共录制 {task_counter - 1} 个任务")


if __name__ == "__main__":
    main()
