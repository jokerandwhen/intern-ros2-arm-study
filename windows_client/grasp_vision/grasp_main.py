"""
视觉抓取主程序
功能：使用OpenCV检测物体，控制SoArm101从动臂抓取物体
"""

import cv2
import time
import numpy as np
from object_detector import ObjectDetector
from arm_controller import ArmController


# ===================== 配置区 =====================
CAMERA_INDEX = 0           # 摄像头索引
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
ARM_PORT = "COM3"          # 主臂串口

# 检测配置
DETECT_COLOR = 'all'       # all, red, blue, green, yellow
MIN_OBJECT_AREA = 500      # 最小检测面积

# 抓取配置
AUTO_GRASP = False         # 是否自动抓取
GRASP_DELAY = 3.0          # 自动抓取延迟（秒）
# ==================================================


def main():
    print("=" * 60)
    print("SoArm101 视觉抓取系统")
    print("=" * 60)

    # 1. 初始化物体检测器
    detector = ObjectDetector()
    print("[OK] 物体检测器已初始化")

    # 2. 初始化机械臂控制器
    arm = ArmController(ARM_PORT)
    if not arm.connect():
        print("[ERROR] 机械臂连接失败，仅运行检测模式")
        arm = None
    else:
        # 回到安全位置
        arm.go_home()
        time.sleep(1)

    # 3. 打开摄像头
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return

    print(f"[OK] 摄像头已打开（索引 {CAMERA_INDEX}）")
    print("\n操作说明：")
    print("  'q' - 退出")
    print("  'c' - 切换检测颜色")
    print("  'g' - 手动抓取最大物体")
    print("  'r' - 释放物体")
    print("  'h' - 回到安全位置")
    print("  'a' - 切换自动抓取模式")
    print("=" * 60)

    last_grasp_time = 0
    detect_color = DETECT_COLOR

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] 摄像头读取失败")
                break

            # 检测物体
            if detect_color == 'all':
                objects = detector.detect_all_colors(frame)
            else:
                objects = detector.detect_by_color(frame, detect_color)

            # 绘制检测结果
            result = detector.draw_detections(frame, objects)

            # 显示信息
            info_lines = [
                f"Detect: {detect_color} | Found: {len(objects)} | Auto: {AUTO_GRASP}",
                "Keys: 'q'uit 'c'olor 'g'rasp 'r'elease 'h'ome 'a'uto"
            ]

            for i, line in enumerate(info_lines):
                cv2.putText(result, line, (10, 30 + i * 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # 显示最大物体的坐标
            target_x, target_y = None, None
            if objects:
                largest = objects[0]
                cx, cy = largest['center']
                arm_x, arm_y = detector.pixel_to_arm_coords(cx, cy, CAMERA_WIDTH, CAMERA_HEIGHT)

                coord_text = f"Target: {largest['color']} at ({cx},{cy}) -> arm({arm_x:.1f}, {arm_y:.1f})"
                cv2.putText(result, coord_text, (10, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                # 在中心画十字
                cv2.line(result, (cx - 15, cy), (cx + 15, cy), (0, 255, 255), 2)
                cv2.line(result, (cx, cy - 15), (cx, cy + 15), (0, 255, 255), 2)

                target_x, target_y = arm_x, arm_y

                # 自动抓取
                if AUTO_GRASP and arm and arm.connected:
                    current_time = time.time()
                    if current_time - last_grasp_time > GRASP_DELAY:
                        print(f"\n[AUTO] 自动抓取: {largest['color']} at ({arm_x:.1f}, {arm_y:.1f})")
                        arm.grasp_object(arm_x, arm_y)
                        last_grasp_time = current_time

            # 显示图像
            cv2.imshow('Grasp Vision', result)

            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                colors = ['all', 'red', 'blue', 'green', 'yellow']
                idx = colors.index(detect_color)
                detect_color = colors[(idx + 1) % len(colors)]
                print(f"[INFO] 切换到: {detect_color}")
            elif key == ord('g'):
                # 手动抓取
                if arm and arm.connected and target_x is not None:
                    print(f"\n[MANUAL] 手动抓取: arm({target_x:.1f}, {target_y:.1f})")
                    arm.grasp_object(target_x, target_y)
                else:
                    print("[WARN] 没有检测到物体或机械臂未连接")
            elif key == ord('r'):
                # 释放物体
                if arm and arm.connected:
                    arm.release_object()
            elif key == ord('h'):
                # 回到安全位置
                if arm and arm.connected:
                    arm.go_home()
            elif key == ord('a'):
                # 切换自动抓取
                AUTO_GRASP = not AUTO_GRASP
                print(f"[INFO] 自动抓取: {'开启' if AUTO_GRASP else '关闭'}")

    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
    finally:
        # 清理
        cap.release()
        cv2.destroyAllWindows()

        if arm and arm.connected:
            arm.go_home()
            time.sleep(1)
            arm.disconnect()

        print("[OK] 程序已退出")


if __name__ == "__main__":
    main()
