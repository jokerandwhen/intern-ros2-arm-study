"""
摄像头测试程序
用于确定哪个摄像头是机械臂摄像头
"""

import cv2
import time

print("=" * 60)
print("摄像头测试程序")
print("=" * 60)
print()

# 检测所有摄像头
cameras = []
for i in range(10):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            cameras.append(i)
            print(f"[{i}] 摄像头 {i} - 可用")
        cap.release()

print()
print(f"检测到 {len(cameras)} 个摄像头")
print()

if not cameras:
    print("[ERROR] 未检测到任何摄像头")
    exit(1)

print("将依次打开每个摄像头，请观察画面确定哪个是机械臂摄像头")
print("按空格键切换到下一个摄像头，按ESC退出")
print()

for idx in cameras:
    print(f"正在打开摄像头 {idx}...")
    cap = cv2.VideoCapture(idx)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    window_name = f"摄像头 {idx} - 按空格切换，按ESC退出"
    cv2.namedWindow(window_name)

    while True:
        ret, frame = cap.read()
        if ret:
            # 在画面上显示摄像头索引
            cv2.putText(frame, f"Camera {idx}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow(window_name, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 32:  # 空格键
            break
        elif key == 27:  # ESC键
            cap.release()
            cv2.destroyAllWindows()
            print()
            print("[INFO] 用户退出")
            exit(0)

    cap.release()
    cv2.destroyAllWindows()

print()
print("=" * 60)
print("测试完成！")
print("请记住机械臂摄像头对应的索引号，然后修改test101.py中的：")
print("  CAMERA_INDEX = <索引号>")
print("=" * 60)