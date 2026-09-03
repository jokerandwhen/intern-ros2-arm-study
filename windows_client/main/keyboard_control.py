"""键盘控制机械臂 - 手动调整每个关节角度"""
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
import cv2
import numpy as np
import time
import msvcrt  # Windows键盘检测

print("="*60)
print("键盘控制机械臂 - 手动调整关节角度")
print("="*60)

# 关节名称和限制
JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
JOINT_MIN = [-180.0, -90.0, -135.0, -90.0, -180.0, 0.0]
JOINT_MAX = [180.0, 90.0, 135.0, 90.0, 180.0, 100.0]

try:
    # 连接机械臂
    print("\n[步骤1] 连接机械臂...")
    config = SOFollowerRobotConfig(port="COM3")
    robot = SOFollower(config)
    robot.connect()
    print("[OK] 连接成功")

    # 读取当前位置
    print("\n[步骤2] 读取当前位置...")
    current_pos = robot.bus.sync_read("Present_Position")
    print(f"当前位置: {current_pos}")

    # 初始化位置（归位到安全位置）
    print("\n[步骤3] 初始化位置...")
    init_angles = [0.0, -30.0, 60.0, 0.0, 0.0, 50.0]  # 安全初始位置
    goal_positions = {
        "shoulder_pan": init_angles[0],
        "shoulder_lift": init_angles[1],
        "elbow_flex": init_angles[2],
        "wrist_flex": init_angles[3],
        "wrist_roll": init_angles[4],
        "gripper": init_angles[5]
    }
    robot.bus.sync_write("Goal_Position", goal_positions)
    print(f"初始化位置: {goal_positions}")
    print("[OK] 等待机械臂移动...")
    time.sleep(2)

    # 初始化角度数组（使用初始位置）
    angles = init_angles.copy()

    # 当前选中的关节
    selected_joint = 0
    angle_step = 5.0  # 每次调整5度

    # 创建显示窗口
    cv2.namedWindow('Keyboard Control', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Keyboard Control', 800, 600)

    print("\n" + "="*60)
    print("按键说明：")
    print("  1-6: 选择关节（底座、肩、肘、腕1、腕2、夹爪）")
    print("  W/↑: 增加角度 (+5°)")
    print("  S/↓: 减小角度 (-5°)")
    print("  Q: 步长改为1°")
    print("  E: 步长改为5°")
    print("  R: 步长改为10°")
    print("  H: 归位（所有关节归零）")
    print("  ESC: 退出")
    print("="*60 + "\n")

    while True:
        # 创建黑色背景
        img = np.zeros((600, 800, 3), dtype=np.uint8)

        # 显示标题
        cv2.putText(img, "Keyboard Control - Joint Angles", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # 显示按键提示
        cv2.putText(img, "Keys: 1-6=Select Joint  W/S=+/-  Q/E/R=Step  H=Home  ESC=Exit", (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # 显示步长
        cv2.putText(img, f"Step: {angle_step}°", (20, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

        # 显示每个关节的角度
        for i in range(6):
            # 选中关节用绿色，未选中用白色
            color = (0, 255, 0) if i == selected_joint else (255, 255, 255)
            thickness = 2 if i == selected_joint else 1

            # 关节名称
            joint_label = f"{i+1}. {JOINT_NAMES[i]}:"

            # 角度值（保留1位小数）
            angle_text = f"{angles[i]:.1f}°"

            # 限制标记
            limit_mark = ""
            if angles[i] <= JOINT_MIN[i] + 1:
                limit_mark = " [MIN]"
            elif angles[i] >= JOINT_MAX[i] - 1:
                limit_mark = " [MAX]"

            # 显示文字（上面）
            y_pos = 150 + i * 70
            cv2.putText(img, joint_label, (20, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, thickness)
            cv2.putText(img, angle_text, (250, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, thickness)

            # 显示限制范围
            range_text = f"[{JOINT_MIN[i]:.0f}° ~ {JOINT_MAX[i]:.0f}°]"
            cv2.putText(img, range_text, (400, y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

            if limit_mark:
                cv2.putText(img, limit_mark, (600, y_pos),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            # 进度条（下面，不遮住文字）
            y_bar = y_pos + 20
            cv2.rectangle(img, (20, y_bar), (700, y_bar + 15), (50, 50, 50), -1)

            # 计算进度条宽度
            progress = (angles[i] - JOINT_MIN[i]) / (JOINT_MAX[i] - JOINT_MIN[i])
            progress = np.clip(progress, 0, 1)
            bar_width = int(progress * 680)

            # 进度条颜色（根据是否选中）
            bar_color = (0, 255, 0) if i == selected_joint else (100, 100, 255)

            # 绘制进度条
            cv2.rectangle(img, (20, y_bar), (20 + bar_width, y_bar + 15), bar_color, -1)

        # 显示画面
        cv2.imshow('Keyboard Control', img)
        cv2.waitKey(1)  # 必须调用waitKey才能更新显示

        # 使用Windows原生键盘检测
        if msvcrt.kbhit():
            key = msvcrt.getch()

            # 处理特殊键（方向键等）
            if key == b'\xe0':  # 特殊键前缀
                key = msvcrt.getch()

            # 处理按键
            if key == b'\x1b':  # ESC
                print("\n[INFO] 用户退出")
                break

            elif key in [b'1', b'2', b'3', b'4', b'5', b'6']:  # 选择关节
                selected_joint = int(key.decode()) - 1
                print(f"[INFO] 选中关节 {selected_joint + 1}: {JOINT_NAMES[selected_joint]}")

            elif key in [b'w', b'W', b'H']:  # W 或 ↑箭头：增加角度
                angles[selected_joint] = min(angles[selected_joint] + angle_step, JOINT_MAX[selected_joint])
                print(f"[INFO] {JOINT_NAMES[selected_joint]}: {angles[selected_joint]:.1f}°")

            elif key in [b's', b'S', b'P']:  # S 或 ↓箭头：减小角度
                angles[selected_joint] = max(angles[selected_joint] - angle_step, JOINT_MIN[selected_joint])
                print(f"[INFO] {JOINT_NAMES[selected_joint]}: {angles[selected_joint]:.1f}°")

            elif key in [b'q', b'Q']:  # Q: 步长1°
                angle_step = 1.0
                print(f"[INFO] 步长改为 {angle_step}°")

            elif key in [b'e', b'E']:  # E: 步长5°
                angle_step = 5.0
                print(f"[INFO] 步长改为 {angle_step}°")

            elif key in [b'r', b'R']:  # R: 步长10°
                angle_step = 10.0
                print(f"[INFO] 步长改为 {angle_step}°")

            elif key in [b'h', b'H']:  # H: 归位
                angles = [0.0, -30.0, 60.0, 0.0, 0.0, 50.0]
                print("[INFO] 所有关节归位")

        # 发送当前角度到机械臂
        goal_positions = {
            "shoulder_pan": float(angles[0]),
            "shoulder_lift": float(angles[1]),
            "elbow_flex": float(angles[2]),
            "wrist_flex": float(angles[3]),
            "wrist_roll": float(angles[4]),
            "gripper": float(angles[5])
        }
        robot.bus.sync_write("Goal_Position", goal_positions)

    # 归位
    print("\n[INFO] 归位中...")
    goal_positions = {
        "shoulder_pan": 0.0,
        "shoulder_lift": 0.0,
        "elbow_flex": 45.0,
        "wrist_flex": 0.0,
        "wrist_roll": 0.0,
        "gripper": 50.0
    }
    robot.bus.sync_write("Goal_Position", goal_positions)
    time.sleep(1)

    robot.disconnect()
    cv2.destroyAllWindows()
    print("[OK] 程序退出")

except Exception as e:
    print(f"\n[ERROR] 程序失败: {e}")
    import traceback
    traceback.print_exc()