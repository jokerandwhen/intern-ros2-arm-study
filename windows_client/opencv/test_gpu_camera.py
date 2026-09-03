"""
诊断脚本：测试GPU加速 + 摄像头帧率 + YOLO检测速度
不控制机械臂，只测试视觉部分
"""
import cv2
import time
import torch
from ultralytics import YOLO

print("=" * 60)
print("GPU + 摄像头 + YOLO 诊断")
print("=" * 60)

# 1. 检查GPU
print(f"\n[1] PyTorch版本: {torch.__version__}")
print(f"    CUDA可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"    GPU: {torch.cuda.get_device_name(0)}")
    print(f"    显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
else:
    print("    ⚠ CUDA不可用！将使用CPU（会很慢）")

# 2. 加载模型
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"\n[2] 加载YOLOv8模型 (device={device})...")
model = YOLO('yolov8n.pt')
print(f"    ✓ 模型已加载，推理设备: {device}")

# 3. 打开摄像头
print(f"\n[3] 打开摄像头...")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not cap.isOpened():
    print("    ✗ 无法打开摄像头0")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("    ✗ 摄像头完全无法打开")
        exit()
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
print("    ✓ 摄像头已打开")

# 4. 预热（第一帧推理总是慢）
print(f"\n[4] 预热模型...")
ret, frame = cap.read()
if ret:
    t0 = time.time()
    model(frame, conf=0.4, verbose=False, imgsz=640, device=device)
    t1 = time.time()
    print(f"    第一帧推理: {1000*(t1-t0):.0f}ms（预热后会快很多）")
    
    # 再跑5次看平均
    times = []
    for _ in range(5):
        ret, frame = cap.read()
        if not ret:
            continue
        t0 = time.time()
        model(frame, conf=0.4, verbose=False, imgsz=640, device=device)
        t1 = time.time()
        times.append(1000*(t1-t0))
    if times:
        print(f"    后续5帧平均: {sum(times)/len(times):.1f}ms")
        print(f"    理论最高FPS: {1000/(sum(times)/len(times)):.0f}")
else:
    print("    ✗ 无法读取画面")

# 5. 实时测试
print(f"\n[5] 实时检测中（按q退出）...")
print(f"    画面左上角会显示FPS和检测信息")

fps_counter = 0
fps_timer = time.time()
current_fps = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("读取失败")
        break
    
    t0 = time.time()
    results = model(frame, conf=0.4, verbose=False, imgsz=640, device=device)
    t1 = time.time()
    infer_ms = 1000 * (t1 - t0)
    
    # 绘制检测结果
    detections = 0
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{conf:.2f}", (x1, y1-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            detections += 1
    
    # FPS计算
    fps_counter += 1
    if time.time() - fps_timer >= 1.0:
        current_fps = fps_counter
        fps_counter = 0
        fps_timer = time.time()
    
    # 显示信息
    info = f"FPS: {current_fps} | Infer: {infer_ms:.0f}ms | Objects: {detections} | Device: {device}"
    cv2.putText(frame, info, (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    # 中心十字
    h, w = frame.shape[:2]
    cv2.line(frame, (w//2-15, h//2), (w//2+15, h//2), (0, 255, 0), 1)
    cv2.line(frame, (w//2, h//2-15), (w//2, h//2+15), (0, 255, 0), 1)
    
    cv2.imshow("GPU Camera Test", frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q') or key == 27:
        break

cap.release()
cv2.destroyAllWindows()
print("\n诊断结束")
