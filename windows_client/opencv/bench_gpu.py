"""
纯性能测试 - 不开GUI窗口，只打印FPS和推理速度
"""
import cv2
import time
import torch
from ultralytics import YOLO

print("=" * 50)
print("性能测试（无GUI）")
print("=" * 50)

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"PyTorch: {torch.__version__}")
print(f"Device: {device}")
if device == 'cuda':
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# 加载模型
model = YOLO('yolov8n.pt')

# 打开摄像头
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# 读取一帧
ret, frame = cap.read()
if not ret:
    print("摄像头无法读取")
    exit()

print(f"\n画面尺寸: {frame.shape}")

# 预热
print("预热中...")
for _ in range(3):
    model(frame, conf=0.4, verbose=False, imgsz=640, device=device)

# 测摄像头原始FPS
print("\n[1] 摄像头原始读取速度...")
t0 = time.time()
count = 0
while time.time() - t0 < 3:
    ret, frame = cap.read()
    count += 1
cam_fps = count / 3
print(f"    摄像头原始FPS: {cam_fps:.1f}")

# 测YOLO推理速度
print("\n[2] YOLO推理速度（GPU）...")
times = []
for _ in range(30):
    ret, frame = cap.read()
    if not ret:
        continue
    t0 = time.time()
    model(frame, conf=0.4, verbose=False, imgsz=640, device=device)
    t1 = time.time()
    times.append(1000 * (t1 - t0))

avg_infer = sum(times) / len(times)
min_infer = min(times)
max_infer = max(times)
print(f"    平均: {avg_infer:.1f}ms")
print(f"    最小: {min_infer:.1f}ms")
print(f"    最大: {max_infer:.1f}ms")
print(f"    理论最高FPS: {1000/avg_infer:.0f}")

# 测完整流程（读取+推理）
print("\n[3] 完整流程速度（读取+推理）...")
t0 = time.time()
count = 0
for _ in range(30):
    ret, frame = cap.read()
    if not ret:
        continue
    model(frame, conf=0.4, verbose=False, imgsz=640, device=device)
    count += 1
total_time = time.time() - t0
full_fps = count / total_time
print(f"    完整流程FPS: {full_fps:.1f}")
print(f"    每帧耗时: {1000*total_time/count:.1f}ms")

cap.release()
print("\n" + "=" * 50)
print(f"结论: {'流畅✓' if full_fps >= 20 else '卡顿✗'} (FPS={full_fps:.1f})")
print("=" * 50)
