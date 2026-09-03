"""
单机械臂控制程序（仅使用COM3）
功能：
1. 连接单个SoArm101机械臂
2. 校准并归位
3. 键盘控制（WASD移动，Q/E旋转，空格夹爪）
"""

import time
import torch
import numpy as np
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

# ===================== 配置区 =====================
ARM_PORT = "COM3"  # 机械臂串口

# 安全参数
JOINT_MIN = -1.0
JOINT_MAX = 1.0
STEP_SIZE = 0.05  # 每次移动步长

# 归位位置
HOME_POSITION = [0.0, -0.3, 0.5, 0.0, 0.0, 0.0]
# ================================================

def home_robot(robot):
    """机械臂归位"""
    print("[INFO] 正在归位...")
    current_pos = np.zeros(6)
    for i in range(20):
        target = current_pos + (np.array(HOME_POSITION) - current_pos) * (i + 1) / 20
        
        # 构造正确的action字典格式
        action = {
            "shoulder_pan.pos": float(target[0]),
            "shoulder_lift.pos": float(target[1]),
            "elbow_flex.pos": float(target[2]),
            "wrist_flex.pos": float(target[3]),
            "wrist_roll.pos": float(target[4]),
            "gripper.pos": float(target[5])
        }
        robot.send_action(action)
        
        current_pos = target
        time.sleep(0.1)
    print("[OK] 归位完成")

def keyboard_control():
    """键盘控制机械臂"""
    print(f"\n[INFO] 正在连接机械臂（{ARM_PORT}）...")

    try:
        config = SOFollowerRobotConfig(port=ARM_PORT)
        robot = SOFollower(config)
        robot.connect()
        print("[OK] 机械臂连接成功")

        # 归位
        home_robot(robot)

        print("\n" + "="*50)
        print("键盘控制模式")
        print("="*50)
        print("控制键：")
        print("  W/S - 肩部升降")
        print("  A/D - 肩部旋转")
        print("  Q/E - 肘部弯曲")
        print("  Z/X - 腕部弯曲")
        print("  C/V - 腕部旋转")
        print("  F/G - 夹爪开合")
        print("  H - 归位")
        print("  ESC - 退出")
        print("="*50 + "\n")

        current_pos = np.array(HOME_POSITION)

        try:
            import keyboard

            while True:
                action = current_pos.copy()

                # 检测按键
                if keyboard.is_pressed('w'):
                    action[1] += STEP_SIZE
                elif keyboard.is_pressed('s'):
                    action[1] -= STEP_SIZE

                if keyboard.is_pressed('a'):
                    action[0] -= STEP_SIZE
                elif keyboard.is_pressed('d'):
                    action[0] += STEP_SIZE

                if keyboard.is_pressed('q'):
                    action[2] -= STEP_SIZE
                elif keyboard.is_pressed('e'):
                    action[2] += STEP_SIZE

                if keyboard.is_pressed('z'):
                    action[3] -= STEP_SIZE
                elif keyboard.is_pressed('x'):
                    action[3] += STEP_SIZE

                if keyboard.is_pressed('c'):
                    action[4] -= STEP_SIZE
                elif keyboard.is_pressed('v'):
                    action[4] += STEP_SIZE

                if keyboard.is_pressed('f'):
                    action[5] -= STEP_SIZE
                elif keyboard.is_pressed('g'):
                    action[5] += STEP_SIZE

                if keyboard.is_pressed('h'):
                    home_robot(robot)
                    current_pos = np.array(HOME_POSITION)
                    continue

                if keyboard.is_pressed('esc'):
                    break

                # 限幅
                action = np.clip(action, JOINT_MIN, JOINT_MAX)

                # 发送动作 - 使用字典格式
                if not np.array_equal(action, current_pos):
                    action_dict = {
                        "shoulder_pan.pos": float(action[0]),
                        "shoulder_lift.pos": float(action[1]),
                        "elbow_flex.pos": float(action[2]),
                        "wrist_flex.pos": float(action[3]),
                        "wrist_roll.pos": float(action[4]),
                        "gripper.pos": float(action[5])
                    }
                    robot.send_action(action_dict)
                    current_pos = action
                    print(f"[INFO] 当前位置: {action[:3]}...")

                time.sleep(0.05)

        except ImportError:
            print("\n[ERROR] 缺少keyboard库，安装方法：pip install keyboard")
            print("[INFO] 程序将在5秒后退出...")
            time.sleep(5)

    except Exception as e:
        print(f"[ERROR] 错误：{e}")

    finally:
        try:
            home_robot(robot)
            robot.disconnect()
            print("\n[OK] 程序已退出，机械臂已归位")
        except:
            pass

if __name__ == "__main__":
    keyboard_control()