"""
摄像头优化测试 - 尝试不同分辨率和编码，找最佳配置
"""
import cv2
import time

print("=" * 50)
print("摄像头优化测试")
print("=" * 50)

# 测试不同配置
configs = [
    {"w": 640, "h": 480, "codec": "MJPG", "desc": "640x480 MJPG"},
    {"w": 640, "h": 480, "codec": "YUYV", "desc": "640x480 YUYV"},
    {"w": 320, "h": 240, "codec": "MJPG", "desc": "320x240 MJPG"},
    {"w": 320, "h": 240, "codec": "YUYV", "desc": "320x240 YUYV"},
]

for cfg in configs:
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    fourcc = cv2.VideoWriter_fourcc(*cfg["codec"])
    cap.set(cv2.CAP_PROP_FOURCC, fourcc)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg["w"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg["h"])
    
    # 读取一帧确认
    ret, frame = cap.read()
    if not ret:
        print(f"  {cfg['desc']}: 无法读取")
        cap.release()
        continue
    
    actual_w, actual_h = frame.shape[1], frame.shape[0]
    
    # 测FPS
    count = 0
    t0 = time.time()
    while time.time() - t0 < 2:
        ret, frame = cap.read()
        if ret:
            count += 1
    fps = count / 2
    
    print(f"  {cfg['desc']}: 实际={actual_w}x{actual_h} FPS={fps:.1f}")
    cap.release()

# 测最佳配置 + YOLO
print("\n" + "=" * 50)
print("最佳配置 + YOLO 测试")
print("=" * 50)

import torch
from ultralytics import YOLO

device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Device: {device}")

model = YOLO('yolov8n.pt')

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 最小缓冲

# 预热
ret, frame = cap.read()
for _ in range(3):
    model(frame, conf=0.4, verbose=False, imgsz=640, device=device)

# 测完整流程
t0 = time.time()
count = 0
for _ in range(30):
    ret, frame = cap.read()
    if not ret:
        continue
    model(frame, conf=0.4, verbose=False, imgsz=640, device=device)
    count += 1
total = time.time() - t0
fps = count / total
print(f"  MJPG + GPU: FPS={fps:.1f} 每帧={1000/fps:.0f}ms")
print(f"  {'流畅✓' if fps >= 25 else '仍卡顿✗'}")

cap.release()
