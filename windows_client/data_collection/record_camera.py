"""
只打开从动臂摄像头进行录制
按 q 键停止录制并保存视频
"""

import cv2
import time
import os
from datetime import datetime

# 摄像头索引（从动臂摄像头）
CAMERA_INDEX = 2

# 录制参数
FPS = 30
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

def main():
    print("=" * 60)
    print("从动臂摄像头录制程序")
    print("=" * 60)

    # 打开摄像头
    print(f"\n正在打开摄像头 index={CAMERA_INDEX}...")
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print(f"错误：无法打开摄像头 index={CAMERA_INDEX}")
        print("\n可能的解决方案：")
        print("1. 确认摄像头USB已连接")
        print("2. 尝试其他索引值（0, 1, 2）")
        print("3. 关闭其他占用摄像头的程序")
        return

    # 设置摄像头参数
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS)

    # 获取实际参数
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = int(cap.get(cv2.CAP_PROP_FPS))

    print(f"✓ 摄像头已打开")
    print(f"  分辨率: {actual_width}x{actual_height}")
    print(f"  帧率: {actual_fps} FPS")

    # 创建保存目录
    save_dir = "camera_recordings"
    os.makedirs(save_dir, exist_ok=True)

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_filename = os.path.join(save_dir, f"follower_camera_{timestamp}.mp4")

    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_filename, fourcc, FPS, (actual_width, actual_height))

    print(f"\n开始录制...")
    print(f"保存路径: {video_filename}")
    print("按 'q' 键停止录制\n")

    # 录制循环
    frame_count = 0
    start_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("警告：无法读取帧")
                break

            # 写入视频
            out.write(frame)

            # 显示预览
            cv2.imshow('Follower Camera', frame)

            # 显示录制信息
            frame_count += 1
            if frame_count % 30 == 0:  # 每秒显示一次
                elapsed_time = time.time() - start_time
                print(f"已录制: {frame_count} 帧 ({elapsed_time:.1f}秒)")

            # 检测按键
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n用户停止录制...")
                break

    except KeyboardInterrupt:
        print("\n程序被中断...")

    finally:
        # 释放资源
        elapsed_time = time.time() - start_time
        cap.release()
        out.release()
        cv2.destroyAllWindows()

        print("\n" + "=" * 60)
        print("录制完成")
        print("=" * 60)
        print(f"总帧数: {frame_count}")
        print(f"总时长: {elapsed_time:.1f}秒")
        print(f"平均帧率: {frame_count/elapsed_time:.1f} FPS")
        print(f"视频文件: {video_filename}")
        print("=" * 60)

if __name__ == "__main__":
    main()