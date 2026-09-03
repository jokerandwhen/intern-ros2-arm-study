"""
YOLOv8 视觉伺服抓取脚本 - 优化版

优化点：
  1. 后台线程持续抓取摄像头画面（ThreadedCamera），画面永不卡住
  2. 隔帧检测：每5帧跑一次YOLO，中间帧用上次结果
  3. 所有arm移动和sleep期间持续刷新画面显示
  4. GPU推理 + device参数

工作流程:
  1. 机械臂移动到搜索位置
  2. YOLO检测画面中的物体，框住最大的可抓取物体
  3. 视觉伺服微调位置，让物体到画面中心
  4. 下降抓取
  5. 移动到放置位置释放

用法:
  python yolo_grasp.py              # 默认摄像头0
  python yolo_grasp.py 0 --conf 0.5
  python yolo_grasp.py 0 --class bottle cup
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


# ============================================================
#  ThreadedCamera: 后台线程持续抓帧，画面永不卡住
# ============================================================
class ThreadedCamera:
    """后台线程持续读取摄像头，read()返回最新帧（非阻塞）"""

    def __init__(self, cam_id=0, width=640, height=480):
        self.cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        # 设置MJPG编码提高帧率
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        # 减少缓冲区大小
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
        """返回最新的 (ret, frame)"""
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
#  全局状态（用于在阻塞期间显示画面）
# ============================================================
_display_state = {
    'cam': None,           # ThreadedCamera 实例
    'last_detections': [], # 最近的检测结果
    'status_text': '',     # 状态文字（如"搜索中..."）
    'grasp_count': 0,
    'device': 'cpu',
    'fps': 0,
}


def show_live_frame(status_text=''):
    """读取最新帧并显示（用于在阻塞操作期间保持画面刷新）"""
    if _display_state['cam'] is None:
        return
    ret, frame = _display_state['cam'].read()
    if not ret or frame is None:
        return

    # 画上最近的检测结果
    frame = draw_detections(frame, _display_state['last_detections'])

    # 中心十字
    h, w = frame.shape[:2]
    cv2.line(frame, (w//2-15, h//2), (w//2+15, h//2), (0, 255, 0), 1)
    cv2.line(frame, (w//2, h//2-15), (w//2, h//2+15), (0, 255, 0), 1)

    # 状态信息
    info = f"FPS:{_display_state['fps']} Obj:{len(_display_state['last_detections'])} Grasp:{_display_state['grasp_count']} {_display_state['device'].upper()}"
    cv2.putText(frame, info, (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    # 额外状态文字
    if status_text:
        cv2.putText(frame, status_text, (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

    cv2.imshow("YOLO Grasp", frame)
    cv2.waitKey(1)


def sleep_with_display(seconds, status_text=''):
    """在sleep期间持续刷新画面"""
    end_time = time.time() + seconds
    while time.time() < end_time:
        show_live_frame(status_text)
        time.sleep(0.03)  # ~30fps刷新


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

        # 在delay期间刷新画面（而非直接sleep）
        sleep_with_display(delay, status_text)


def write_positions_with_display(arm, positions, wait=0.3, status_text=''):
    """写入位置后在等待期间持续刷新画面"""
    arm._sync_write_positions(positions)
    sleep_with_display(wait, status_text)


# ============================================================
#  核心功能函数
# ============================================================
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

def main():
    parser = argparse.ArgumentParser(description="YOLO视觉伺服抓取")
    parser.add_argument("cam", type=int, nargs="?", default=0, help="摄像头编号")
    parser.add_argument("--conf", type=float, default=0.4, help="置信度阈值")
    parser.add_argument("--class", dest="classes", nargs="*", help="只检测指定类别")
    args = parser.parse_args()

    target_classes = set(args.classes) if args.classes else None

    print("=" * 60)
    print("SoArm101 YOLO视觉伺服抓取")
    print("=" * 60)

    # 加载配置
    positions = load_json(POSITIONS_FILE)
    search_poses = load_json(SEARCH_FILE)

    if 'home' not in positions:
        print("\n缺少 home 位置")
        return
    if not search_poses:
        print("\n未找到搜索位置，请先运行: python setup_search.py")
        return

    print(f"\n摄像头: {args.cam}（夹爪摄像头）")
    print(f"置信度: {args.conf}")
    print(f"目标物体: {', '.join(target_classes) if target_classes else '全部可抓取物体'}")
    print(f"搜索位置: {', '.join(search_poses.keys())}")

    # 打开摄像头（使用ThreadedCamera，后台持续抓帧）
    print("\n打开摄像头（后台线程抓帧）...")
    cam = ThreadedCamera(args.cam, 640, 480)
    if not cam.isOpened():
        print("无法打开摄像头")
        return

    # 设置全局显示状态
    _display_state['cam'] = cam

    # 等摄像头就绪
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
    sleep_with_display(0.3, 'Enabling torque...')
    arm.enable_torque()

    # 移动到home
    print("移动到home...")
    move_smooth_with_display(arm, positions['home'], steps=20, delay=0.03, status_text='Moving to home...')
    sleep_with_display(0.3, 'Ready')

    print("\n" + "=" * 60)
    print("YOLO视觉抓取已启动！")
    print("=" * 60)
    print("  g     - 开始搜索并抓取")
    print("  h     - 回到home")
    print("  q/Esc - 退出")
    print("=" * 60)

    grasp_count = 0
    frame_count = 0
    last_detections = []
    DETECT_INTERVAL = 5  # 每5帧检测一次

    fps_timer = time.time()
    fps_count = 0
    current_fps = 0

    while True:
        ret, frame = cam.read()
        if not ret:
            time.sleep(0.01)
            continue

        frame_count += 1
        fps_count += 1

        # 隔帧检测：只在 DETECT_INTERVAL 的倍数帧运行 YOLO
        if frame_count % DETECT_INTERVAL == 0:
            detections = detect_objects(model, frame, args.conf, target_classes, device)
            if not target_classes:
                detections = [d for d in detections if d['class'] in GRASPABLE]
            last_detections = detections
            _display_state['last_detections'] = detections

        # 用最新检测结果画框
        frame = draw_detections(frame, last_detections)

        # FPS计算
        if time.time() - fps_timer >= 1.0:
            current_fps = fps_count
            fps_count = 0
            fps_timer = time.time()
            _display_state['fps'] = current_fps

        # 中心十字
        h, w = frame.shape[:2]
        cv2.line(frame, (w//2-15, h//2), (w//2+15, h//2), (0, 255, 0), 1)
        cv2.line(frame, (w//2, h//2-15), (w//2, h//2+15), (0, 255, 0), 1)

        info = f"FPS:{current_fps} Obj:{len(last_detections)} Grasp:{grasp_count} {device.upper()}"
        cv2.putText(frame, info, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        cv2.imshow("YOLO Grasp", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('g'):
            print("\n开始搜索物体（按q可随时取消）...")
            _display_state['grasp_count'] = grasp_count
            while True:
                success = search_and_grasp_yolo(
                    arm, cam, model, args.conf, target_classes, positions, search_poses, device)
                if success:
                    grasp_count += 1
                    _display_state['grasp_count'] = grasp_count
                    print(f"✓ 抓取成功! (第{grasp_count}次)")
                    break
                else:
                    print("✗ 本次未成功，2秒后自动重试（按q取消）...")
                    cancel = False
                    sleep_with_display(2.0, 'Retrying in 2s...')
                    # 检查是否按了q
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("已取消")
                        break
                    print("\n重新开始搜索...")
            # 搜索结束后回到home
            move_smooth_with_display(arm, positions['home'], steps=20, delay=0.03, status_text='Moving to home...')
        elif key == ord('h'):
            print("\n回到home...")
            move_smooth_with_display(arm, positions['home'], steps=20, delay=0.03, status_text='Moving to home...')

    cam.release()
    cv2.destroyAllWindows()
    print("\n回到home...")
    move_smooth_with_display(arm, positions['home'], steps=20, delay=0.03, status_text='Moving to home...')
    arm.disable_torque()
    arm.disconnect()
    print(f"\n完成! 共抓取 {grasp_count} 次")

def search_and_grasp_yolo(arm, cam, model, conf, target_classes, positions, search_poses, device='cpu'):
    """搜索物体并抓取（只在search1位置）"""

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

        # 实时显示画面 + 提示
        frame = draw_detections(frame, _display_state['last_detections'])
        h, w = frame.shape[:2]
        cv2.line(frame, (w//2-15, h//2), (w//2+15, h//2), (0, 255, 0), 1)
        cv2.line(frame, (w//2, h//2-15), (w//2, h//2+15), (0, 255, 0), 1)
        cv2.putText(frame, "Put object in view, press [SPACE] to detect", (60, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, "[q] cancel", (220, 280),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.imshow("YOLO Grasp", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord(' ') or key == 13:  # 空格或回车
            waiting = False
        elif key == ord('q') or key == 27:
            print("  已取消")
            return False

    # 持续检测多帧，直到找到物体或达到最大次数
    print("  持续检测中（共尝试10次）...")
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

        # 实时显示检测画面
        frame = draw_detections(frame, detections)
        h, w = frame.shape[:2]
        cv2.line(frame, (w//2-15, h//2), (w//2+15, h//2), (0, 255, 0), 1)
        cv2.line(frame, (w//2, h//2-15), (w//2, h//2+15), (0, 255, 0), 1)
        cv2.putText(frame, f"Detecting {attempt+1}/10  Found:{len(detections)}", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.imshow("YOLO Grasp", frame)
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

    # 视觉伺服
    print(f"    视觉伺服对准中...")
    aligned, adjusted_pose = visual_servo_yolo(arm, cam, model, conf, target_classes, search_pose, device)

    if not aligned:
        print(f"    对准失败")
        return False

    print(f"    对准成功! 开始抓取...")
    return execute_grasp(arm, adjusted_pose, positions, cam)

def visual_servo_yolo(arm, cam, model, conf, target_classes, start_pose, device='cpu', max_iters=15):
    """YOLO视觉伺服，返回 (是否对准, 调整后的pose)。
    
    逻辑：
    1. 连续观察多帧，确认物体位置稳定
    2. 如果某帧丢失，继续观察而不是直接抓
    3. 只有当连续3帧都检测到物体且位置稳定时才认为对准
    4. 如果多次迭代后仍未稳定，才放弃
    """
    current_pose = start_pose.copy()
    PAN_STEP = 30
    DEAD_ZONE = 30
    STABLE_FRAMES = 3  # 需要连续稳定3帧
    
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
        cv2.imshow("YOLO Grasp", frame)
        cv2.waitKey(1)

        if not detections:
            print(f"      迭代{i+1}: 物体丢失，继续观察...")
            stable_count = 0  # 重置稳定计数
            sleep_with_display(0.3, 'Waiting for object...')
            continue

        best = max(detections, key=lambda x: x['area'])
        cx, cy = best['center']
        dx = cx - cx_center

        print(f"      迭代{i+1}: ({cx},{cy}) dx={dx:+4d} stable={stable_count}/{STABLE_FRAMES} {best['class']}")

        # 检查是否稳定（连续几帧dx变化不大且在死区内）
        if abs(dx) < DEAD_ZONE and abs(dx - last_dx) < 20:
            stable_count += 1
            if stable_count >= STABLE_FRAMES:
                print(f"      ✓ 连续{STABLE_FRAMES}帧稳定，对准了!")
                return True, current_pose
        else:
            stable_count = 0

        last_dx = dx

        # pan方向：物体在画面右边(dx>0)→pan值增大（机械臂往左转，让摄像头转向右边）
        step = PAN_STEP if dx > 0 else -PAN_STEP
        step = int(step * min(abs(dx) / 100, 2))
        new_val = max(0, min(4095, current_pose[1] + step))
        if new_val != current_pose[1]:
            current_pose[1] = new_val

        write_positions_with_display(arm, current_pose, wait=0.4,
                                      status_text=f'Servo {i+1}: adjusting pan...')

    print(f"      达到最大迭代，未稳定")
    return False, current_pose

def execute_grasp(arm, current_pose, positions, cam=None):
    """执行抓取：从搜索位置直接下降抓取，保持pan方向不变"""
    try:
        # current_pose 是视觉伺服调整后的搜索位置（pan已对准物体方向）
        # 从搜索位置直接下降抓取，不转到反方向的grasp位置

        # [1/5] 在当前位置张开夹爪
        print("    [1/5] 张开夹爪...")
        open_pose = current_pose.copy()
        open_pose[6] = 1258  # 张开夹爪
        write_positions_with_display(arm, open_pose, wait=0.5, status_text='[1/5] Opening gripper...')

        # [2/5] 弯曲elbow下降 + 调整wrist让夹爪朝下
        # 搜索位置elbow=3045（伸直），弯曲到约1600下降到桌面
        # wrist从2847调整到约1500让夹爪从朝前变成朝下
        print("    [2/5] 下降到物体...")
        down = open_pose.copy()
        down[3] = max(0, open_pose[3] - 1400)  # elbow弯曲下降（3045→1645）
        down[4] = max(0, open_pose[4] - 1300)  # wrist调整让夹爪朝下（2847→1547）
        move_smooth_with_display(arm, down, steps=25, delay=0.04, status_text='[2/5] Descending...')

        # [3/5] 闭合夹爪
        print("    [3/5] 闭合夹爪...")
        close = down.copy()
        close[6] = 1740
        write_positions_with_display(arm, close, wait=0.8, status_text='[3/5] Closing gripper...')

        # [4/5] 抬起（elbow和wrist回到搜索位置的高度）
        print("    [4/5] 抬起...")
        lift = close.copy()
        lift[3] = open_pose[3]  # elbow回到搜索位置
        lift[4] = open_pose[4]  # wrist回到搜索位置
        move_smooth_with_display(arm, lift, steps=15, delay=0.04, status_text='[4/5] Lifting...')

        # [5/5] 慢慢回home
        print("    [5/5] 慢慢回home...")
        if 'home' in positions:
            move_smooth_with_display(arm, positions['home'], steps=30, delay=0.05,
                                      status_text='[5/5] Returning home...')

        return True
    except Exception as e:
        print(f"    抓取出错: {e}")
        return False

if __name__ == "__main__":
    main()
