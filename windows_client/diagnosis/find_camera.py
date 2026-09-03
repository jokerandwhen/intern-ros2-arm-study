"""
扫描所有可用的摄像头设备
帮助找到正确的摄像头索引
"""

import cv2

print("=" * 60)
print("摄像头设备扫描程序")
print("=" * 60)

print("\n正在扫描摄像头设备（索引 0-9）...\n")

available_cameras = []

for index in range(10):
    cap = cv2.VideoCapture(index)
    if cap.isOpened():
        # 读取一帧测试
        ret, frame = cap.read()
        if ret:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))

            available_cameras.append(index)
            print(f"✓ 找到摄像头 index={index}")
            print(f"  分辨率: {width}x{height}")
            print(f"  帧率: {fps} FPS")
            print(f"  状态: 可用\n")
        else:
            print(f"⚠ 摄像头 index={index} 可打开但无法读取帧\n")

        cap.release()
    else:
        pass  # 该索引无设备

print("=" * 60)
print(f"扫描完成：找到 {len(available_cameras)} 个可用摄像头")
print(f"可用摄像头索引: {available_cameras}")
print("=" * 60)

if not available_cameras:
    print("\n未找到任何摄像头！")
    print("可能的原因：")
    print("1. 摄像头USB未连接")
    print("2. 摄像头被其他程序占用")
    print("3. 驱动程序问题")

# 尝试打开第一个可用的摄像头进行预览
if available_cameras:
    test_index = available_cameras[0]
    print(f"\n正在打开摄像头 index={test_index} 进行预览...")
    print("按 'q' 键关闭预览窗口\n")

    cap = cv2.VideoCapture(test_index)

    if cap.isOpened():
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            cv2.imshow(f'Camera Preview (index={test_index})', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

print("\n程序结束")