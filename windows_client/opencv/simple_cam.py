"""
最简单的摄像头测试 - 不加YOLO，只看画面能不能动
"""
import cv2
import time

print("简单摄像头测试（无YOLO）")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

frame_count = 0
t0 = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        print("读取失败")
        break
    
    frame_count += 1
    if frame_count % 30 == 0:
        fps = frame_count / (time.time() - t0)
        print(f"  FPS: {fps:.1f}  frames: {frame_count}")
    
    cv2.putText(frame, f"FPS: {frame_count / (time.time() - t0):.1f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    cv2.imshow("Camera Test", frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q') or key == 27:
        break

cap.release()
cv2.destroyAllWindows()
print(f"总帧数: {frame_count}, FPS: {frame_count / (time.time() - t0):.1f}")
