"""详细诊断摄像头问题"""
import cv2

print("=" * 50)
print("摄像头详细诊断")
print("=" * 50)

for i in range(10):
    print(f"\n--- 摄像头 {i} ---")
    try:
        cap = cv2.VideoCapture(i)
        if cap is None:
            print("  cv2.VideoCapture返回None")
            continue

        is_open = cap.isOpened()
        print(f"  isOpened: {is_open}")

        if is_open:
            ret, frame = cap.read()
            print(f"  read返回: ret={ret}")
            if ret:
                h, w = frame.shape[:2]
                print(f"  分辨率: {w}x{h}")
                print(f"  帧类型: {type(frame)}, dtype: {frame.dtype}")
            else:
                print("  ❌ 能打开但读取失败（可能被占用）")
            cap.release()
        else:
            print("  ❌ 无法打开（设备不存在或被占用）")
            # 尝试强制打开
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            if cap.open(i):
                print("  ✓ 强制打开成功")
                cap.release()
            else:
                print("  强制打开也失败")
    except Exception as e:
        print(f"  ❌ 异常: {e}")

print("\n" + "=" * 50)
print("常见原因：")
print("1. 摄像头被其他程序占用（如另一个python进程）")
print("2. USB线松动或供电不足")
print("3. 驱动问题")
print("4. 摄像头索引不连续（0和2可用，1不可用是正常的）")
