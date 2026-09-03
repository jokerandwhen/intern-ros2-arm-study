"""检查SoArm101舵机状态"""
import sys

try:
    from lerobot.robots.so_follower.so_follower import SOFollower
    from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
    import time

    print("[INFO] 正在连接SoArm101...")
    config = SOFollowerRobotConfig(port="COM3")
    robot = SOFollower(config)
    robot.connect()

    print("[OK] 连接成功")
    print("\n正在检测舵机...")

    # 尝试读取舵机状态
    try:
        # 获取连接的舵机信息
        if hasattr(robot, 'bus'):
            print(f"舵机总线: {robot.bus}")
            if hasattr(robot.bus, 'motors'):
                print(f"配置的舵机: {robot.bus.motors}")

            # 尝试扫描舵机
            print("\n正在扫描舵机（ID 1-10）...")
            for motor_id in range(1, 11):
                try:
                    # 尝试读取位置
                    if hasattr(robot.bus, 'read'):
                        pos = robot.bus.read("Present_Position", motor_id)
                        print(f"  [OK] 舵机ID {motor_id}: 位置={pos}")
                except Exception as e:
                    pass  # 该ID没有舵机，跳过

        # 尝试获取当前动作
        print("\n尝试读取当前动作...")
        try:
            action = robot.get_action()
            print(f"[OK] 当前动作: {action}")
        except Exception as e:
            print(f"[WARN] 无法读取动作: {e}")

    except Exception as e:
        print(f"[ERROR] 检测舵机失败: {e}")
        import traceback
        traceback.print_exc()

    robot.disconnect()
    print("\n[INFO] 检测完成")

except Exception as e:
    print(f"[ERROR] 程序失败: {e}")
    import traceback
    traceback.print_exc()