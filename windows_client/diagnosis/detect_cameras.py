"""检测所有可用摄像头"""
import cv2

print("正在检测摄像头...\n")
available = []
for i in range(10):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"  摄像头 {i}: 可用 ({w}x{h})")
            available.append(i)
        cap.release()

print(f"\n共检测到 {len(available)} 个可用摄像头: {available}")
