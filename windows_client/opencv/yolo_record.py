"""
YOLO视觉检测 + 手动录制抓取动作

流程:
  1. YOLO检测物体并视觉伺服对准
  2. 对准后禁用扭矩，进入录制模式
  3. 手动操作从动臂完成抓取动作
  4. 按Esc停止录制，保存动作
  5. 可以回放录制的动作

用法:
  python yolo_record.py record [任务名]   # 检测物体并录制抓取动作
  python yolo_record.py replay [任务名]   # 回放录制的动作
  python yolo_record.py list              # 查看已录制的任务
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
SEARCH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_poses.json")
RECORDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "records")
RECORD_FREQ = 20  # 录制频率 Hz

# 全局显示状态
_display_state = {
    'cam': None,
    'last_detections': [],
    'grasp_count': 0,
    'device': 'cpu',
    'fps': 0,
}


class ThreadedCamera:
    """后台线程持续读取摄像头"""

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


def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {name: {int(k): v for k, v in pos.items()} for name, pos in data.items()}
    return {}


def detect_objects(model, frame, conf_threshold=0.4, target_classes=None, device='cpu'):
    """用YOLO检测物体"""
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
    """绘制检测结果"""
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


def show_live_frame(status_text=''):
    """读取最新帧并显示"""
    if _display_state['cam'] is None:
        return
    ret, frame = _display_state['cam'].read()
    if not ret or frame is None:
        return

    frame = draw_detections(frame, _display_state['last_detections'])
    h, w = frame.shape[:2]
    cv2.line(frame, (w//2-15, h//2), (w//2+15, h//2), (0, 255, 0), 1)
    cv2.line(frame, (w//2, h//2-15), (w//2, h//2+15), (0, 255, 0), 1)

    info = f"FPS:{_display_state['fps']} Obj:{len(_display_state['last_detections'])} {_display_state['device'].upper()}"
    cv2.putText(frame, info, (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    if status_text:
        cv2.putText(frame, status_text, (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

    cv2.imshow("YOLO Record", frame)
    cv2.waitKey(1)


def sleep_with_display(seconds, status_text=''):
    """在sleep期间持续刷新画面"""
    end_time = time.time() + seconds
    while time.time() < end_time:
        show_live_frame(status_text)
        time.sleep(0.03)


def move_smooth_with_display(arm, target_positions, steps=20, delay=0.03, status_text=''):
    """平滑移动机械臂，移动期间持续刷新摄像头画面"""
    current = arm.read_all_positions()

    for step in range(1, steps + 1):
        t = step / steps
        target = {}
        for mid in range(1, 7):
            if mid in target_positions:
                start = current.get(mid, 2048)
                end = target_positions[mid]
                target[mid] = int(start + (end - start) * t)
            else:
                target[mid] = current.get(mid, 2048)

        arm._sync_write_positions(target)
        sleep_with_display(delay, status_text)


def write_positions_with_display(arm, positions, wait=0.3, status_text=''):
    """写入位置后在等待期间持续刷新画面"""
    arm._sync_write_positions(positions)
    sleep_with_display(wait, status_text)


def ensure_records_dir():
    if not os.path.exists(RECORDS_DIR):
        os.makedirs(RECORDS_DIR)


def get_record_path(name):
    return os.path.join(RECORDS_DIR, f"{name}.json")


def list_records():
    ensure_records_dir()
    files = [f[:-5] for f in os.listdir(RECORDS_DIR) if f.endswith('.json')]
    return sorted(files)


def record_grasp(arm, cam, model, conf, target_classes, search_poses, device, task_name):
    """检测物体并录制抓取动作"""
    
    if 'search1' not in search_poses:
        print("  缺少 search1 位置")
        return False

    search_pose = search_poses['search1']

    print(f"\n  移动到 search1 ...")
    move_smooth_with_display(arm, search_pose, steps=20, delay=0.03,
                              status_text='Moving to search1...')

    # 等待用户放好物体后按空格继续
    print("  请在摄像头前放好物体，然后按【空格】开始检测，按【q】取消")
    waiting = True
    while waiting:
        ret, frame = cam.read()
        if not ret:
            sleep_with_display(0.1, 'Waiting...')
            continue

        frame = draw_detections(frame, _display_state['last_detections'])
        h, w = frame.shape[:2]
        cv2.line(frame, (w//2-15, h//2), (w//2+15, h//2), (0, 255, 0), 1)
        cv2.line(frame, (w//2, h//2-15), (w//2, h//2+15), (0, 255, 0), 1)
        cv2.putText(frame, "Put object in view, press [SPACE] to detect", (60, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, "[q] cancel", (220, 280),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.imshow("YOLO Record", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord(' ') or key == 13:
            waiting = False
        elif key == ord('q') or key == 27:
            print("  已取消")
            return False

    # 持续检测多帧
    print("  持续检测中...")
    detections = []
    for attempt in range(10):
        ret, frame = cam.read()
        if not ret:
            sleep_with_display(0.1, f'Detecting {attempt+1}/10...')
            continue

        detections = detect_objects(model, frame, conf, target_classes, device)
        if not target_classes:
            detections = [d for d in detections if d['class'] in GRASPABLE]

        _display_state['last_detections'] = detections

        frame = draw_detections(frame, detections)
        h, w = frame.shape[:2]
        cv2.line(frame, (w//2-15, h//2), (w//2+15, h//2), (0, 255, 0), 1)
        cv2.line(frame, (w//2, h//2-15), (w//2, h//2+15), (0, 255, 0), 1)
        cv2.putText(frame, f"Detecting {attempt+1}/10  Found:{len(detections)}", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.imshow("YOLO Record", frame)
        cv2.waitKey(1)

        if detections:
            break
        sleep_with_display(0.15, f'Detecting {attempt+1}/10...')

    if not detections:
        print(f"    未检测到物体")
        sleep_with_display(1.0, 'No object detected')
        return False

    best = max(detections, key=lambda x: x['area'])
    cx, cy = best['center']
    print(f"    发现 {best['class']}! 位置=({cx},{cy}) 置信度={best['conf']:.2f}")

    # 视觉伺服对准
    print(f"    视觉伺服对准中...")
    aligned, adjusted_pose = visual_servo_yolo(arm, cam, model, conf, target_classes, search_pose, device)

    if not aligned:
        print(f"    对准失败")
        return False

    print(f"    对准成功! 进入录制模式...")

    # 禁用扭矩，进入录制模式
    print("\n" + "=" * 60)
    print(f"录制模式: {task_name}")
    print("=" * 60)
    print("禁用扭矩，你可以手动移动机械臂...")
    arm.disable_torque()
    time.sleep(0.5)

    start_pos = arm.read_all_positions_fast()
    print(f"\n起始位置: {start_pos}")
    print(f"\n录制频率: {RECORD_FREQ} Hz (每秒{RECORD_FREQ}帧)")
    print("\n操作说明:")
    print("  1. 手动移动机械臂完成抓取动作")
    print("  2. 按 Esc 停止录制")
    print()

    frames = []
    start_time = time.time()
    frame_interval = 1.0 / RECORD_FREQ

    print("录制中... (按 Esc 停止)")
    print(f"{'时间':>6}s  {'帧数':>5}  shoulder  lift   elbow  wrist_f wrist_r gripper")
    print("-" * 75)

    try:
        next_frame_time = start_time
        while True:
            # 检查Esc键
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\x1b':  # Esc
                    break

            current_time = time.time()
            elapsed = current_time - start_time

            # 读取位置（高速）
            pos = arm.read_all_positions_fast()
            frames.append({
                't': round(elapsed, 4),
                'pos': {str(k): v for k, v in pos.items()}
            })

            # 打印进度
            if len(frames) % 10 == 1:
                print(f"{elapsed:6.2f}s  {len(frames):5d}  "
                      f"{pos[1]:7d}  {pos[2]:5d}  {pos[3]:5d}  "
                      f"{pos[4]:6d}  {pos[5]:6d}  {pos[6]:6d}")

            # 等待下一帧
            next_frame_time += frame_interval
            sleep_time = next_frame_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        pass

    duration = time.time() - start_time
    print("-" * 75)
    print(f"\n录制完成!")
    print(f"  总时长: {duration:.2f}s")
    print(f"  总帧数: {len(frames)}")
    print(f"  实际频率: {len(frames)/duration:.1f} Hz")

    if len(frames) < 2:
        print("\n录制太短，未保存")
        return False

    # 保存
    ensure_records_dir()
    record_data = {
        'name': task_name,
        'freq': RECORD_FREQ,
        'duration': round(duration, 2),
        'frames': len(frames),
        'data': frames,
        'start_pose': {str(k): v for k, v in adjusted_pose.items()}  # 保存视觉伺服后的位置
    }

    path = get_record_path(task_name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(record_data, f, indent=2)
    print(f"  已保存到: {path}")

    return True


def visual_servo_yolo(arm, cam, model, conf, target_classes, start_pose, device='cpu', max_iters=15):
    """YOLO视觉伺服"""
    current_pose = start_pose.copy()
    PAN_STEP = 30
    DEAD_ZONE = 30
    STABLE_FRAMES = 3

    stable_count = 0
    last_dx = 0

    for i in range(max_iters):
        ret, frame = cam.read()
        if not ret:
            sleep_with_display(0.1, 'Servo: frame lost')
            continue

        h, w = frame.shape[:2]
        cx_center, cy_center = w // 2, h // 2

        detections = detect_objects(model, frame, conf, target_classes, device)
        if not target_classes:
            detections = [d for d in detections if d['class'] in GRASPABLE]

        _display_state['last_detections'] = detections

        frame = draw_detections(frame, detections)
        cv2.line(frame, (cx_center-15, cy_center), (cx_center+15, cy_center), (0, 255, 0), 1)
        cv2.line(frame, (cx_center, cy_center-15), (cx_center, cy_center+15), (0, 255, 0), 1)
        cv2.putText(frame, f"Servo {i+1}/{max_iters} Stable:{stable_count}/{STABLE_FRAMES}", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
        cv2.imshow("YOLO Record", frame)
        cv2.waitKey(1)

        if not detections:
            print(f"      迭代{i+1}: 物体丢失，继续观察...")
            stable_count = 0
            sleep_with_display(0.3, 'Waiting for object...')
            continue

        best = max(detections, key=lambda x: x['area'])
        cx, cy = best['center']
        dx = cx - cx_center

        print(f"      迭代{i+1}: ({cx},{cy}) dx={dx:+4d} stable={stable_count}/{STABLE_FRAMES} {best['class']}")

        if abs(dx) < DEAD_ZONE and abs(dx - last_dx) < 20:
            stable_count += 1
            if stable_count >= STABLE_FRAMES:
                print(f"      ✓ 连续{STABLE_FRAMES}帧稳定，对准了!")
                return True, current_pose
        else:
            stable_count = 0

        last_dx = dx

        # pan方向：物体在画面右边(dx>0)→pan值增大
        step = PAN_STEP if dx > 0 else -PAN_STEP
        step = int(step * min(abs(dx) / 100, 2))
        new_val = max(0, min(4095, current_pose[1] + step))
        if new_val != current_pose[1]:
            current_pose[1] = new_val

        write_positions_with_display(arm, current_pose, wait=0.4,
                                      status_text=f'Servo {i+1}: adjusting pan...')

    print(f"      达到最大迭代，未稳定")
    return False, current_pose


def replay_grasp(arm, cam, task_name):
    """回放录制的抓取动作"""
    path = get_record_path(task_name)
    if not os.path.exists(path):
        print(f"\n录制 '{task_name}' 不存在")
        print(f"可用录制: {', '.join(list_records())}")
        return

    with open(path, 'r', encoding='utf-8') as f:
        record_data = json.load(f)

    frames = record_data['data']
    duration = record_data['duration']
    start_pose = {int(k): v for k, v in record_data.get('start_pose', {}).items()}

    print("\n" + "=" * 60)
    print(f"回放模式: {task_name}")
    print("=" * 60)
    print(f"  录制时长: {duration}s")
    print(f"  帧数: {len(frames)}")
    if start_pose:
        print(f"  起始位置: {start_pose}")

    print("\n操作说明:")
    print("  1. 确认机械臂当前位置与录制起始位置接近")
    print("  2. 按 Enter 开始回放")
    print("  3. 按 Ctrl+C 可随时停止")

    input("\n准备好后按 Enter 开始回放...")

    # 使能扭矩
    print("使能扭矩...")
    arm.enable_torque()
    time.sleep(0.5)

    # 先平滑移动到起始位置
    if start_pose:
        print("移动到起始位置...")
        move_smooth_with_display(arm, start_pose, steps=20, delay=0.03, status_text='Moving to start...')
        time.sleep(0.3)

    print("\n回放中...")
    print(f"{'时间':>6}s  {'帧':>5}/{len(frames)}  shoulder  lift   elbow  wrist_f wrist_r gripper")
    print("-" * 75)

    start_time = time.time()
    frame_interval = 1.0 / record_data['freq']

    try:
        for i, frame in enumerate(frames):
            target = {int(k): v for k, v in frame['pos'].items()}
            arm._sync_write_positions(target)

            elapsed = time.time() - start_time

            if (i + 1) % 10 == 0 or i == 0 or i == len(frames) - 1:
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

    except KeyboardInterrupt:
        print("\n\n回放被中断")

    finally:
        arm.disable_torque()


def main():
    parser = argparse.ArgumentParser(description="YOLO视觉检测 + 手动录制抓取动作")
    parser.add_argument("cmd", choices=["record", "replay", "list"], help="命令")
    parser.add_argument("name", nargs="?", default="grasp1", help="任务名称")
    parser.add_argument("--cam", type=int, default=0, help="摄像头编号")
    parser.add_argument("--conf", type=float, default=0.4, help="置信度阈值")
    args = parser.parse_args()

    if args.cmd == 'list':
        records = list_records()
        if records:
            print("\n已录制动作:")
            for r in records:
                path = get_record_path(r)
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"  {r:<20} {data['duration']}s  {data['frames']}帧")
        else:
            print("\n暂无录制")
        return

    print("=" * 60)
    print("YOLO视觉检测 + 手动录制抓取动作")
    print("=" * 60)

    # 加载配置
    search_poses = load_json(SEARCH_FILE)
    if not search_poses:
        print("\n未找到搜索位置，请先运行: python setup_search.py")
        return

    # 打开摄像头
    print("\n打开摄像头...")
    cam = ThreadedCamera(args.cam, 640, 480)
    if not cam.isOpened():
        print("无法打开摄像头")
        return

    _display_state['cam'] = cam
    sleep_with_display(0.5, 'Opening camera...')

    # 加载模型
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"加载YOLOv8模型 (device={device})...")
    sleep_with_display(0.1, 'Loading YOLO model...')
    model = YOLO('yolov8n.pt')
    print(f"✓ 模型已加载，使用 {'GPU: ' + torch.cuda.get_device_name(0) if device == 'cuda' else 'CPU'}")
    _display_state['device'] = device

    # 预热模型
    print("预热YOLO模型...")
    ret, frame = cam.read()
    if ret:
        sleep_with_display(0.1, 'Warming up YOLO...')
        model(frame, conf=args.conf, verbose=False, imgsz=640, device=device)
    print("✓ 预热完成")

    # 连接机械臂
    print("连接机械臂...")
    sleep_with_display(0.1, 'Connecting arm...')
    arm = SoArmController(port="COM3")
    arm.connect()
    time.sleep(0.3)
    arm.enable_torque()

    try:
        if args.cmd == 'record':
            print(f"\n任务名称: {args.name}")
            record_grasp(arm, cam, model, args.conf, None, search_poses, device, args.name)
        elif args.cmd == 'replay':
            replay_grasp(arm, cam, args.name)

    finally:
        print("\n回到home...")
        positions = load_json(POSITIONS_FILE)
        if 'home' in positions:
            move_smooth_with_display(arm, positions['home'], steps=20, delay=0.03, status_text='Moving to home...')
        arm.disable_torque()
        arm.disconnect()
        cam.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
