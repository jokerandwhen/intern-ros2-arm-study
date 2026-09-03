"""测试舵机直接写入"""
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
import time

print("="*60)
print("舵机直接写入测试")
print("="*60)

try:
    print("\n[步骤1] 连接控制板...")
    config = SOFollowerRobotConfig(port="COM3")
    robot = SOFollower(config)
    robot.connect()
    print("[OK] 连接成功")

    # 读取当前位置
    print("\n[步骤2] 读取当前位置...")
    current_pos = robot.bus.sync_read("Present_Position")
    print(f"当前位置: {current_pos}")

    # 尝试直接写入舵机总线
    print("\n[步骤3] 尝试直接写入舵机总线...")

    # 方法1：使用sync_write
    try:
        # 构造目标位置（使用当前读取到的值）
        goal_positions = {
            "shoulder_pan": current_pos["shoulder_pan"],
            "shoulder_lift": current_pos["shoulder_lift"],
            "elbow_flex": current_pos["elbow_flex"],
            "wrist_flex": current_pos["wrist_flex"],
            "wrist_roll": current_pos["wrist_roll"],
            "gripper": current_pos["gripper"]
        }

        print(f"目标位置: {goal_positions}")
        robot.bus.sync_write("Goal_Position", goal_positions)
        print("[OK] sync_write 写入成功！")

    except Exception as e:
        print(f"[ERROR] sync_write 失败: {e}")

        # 方法2：尝试逐个写入
        print("\n[尝试方法2] 逐个写入...")
        for name, pos in goal_positions.items():
            try:
                motor = robot.bus.motors[name]
                print(f"  写入 {name} (ID={motor.id}): 位置={pos}")
                # 使用底层写入
                robot.bus.write_with_motor_id(
                    motor_model=motor.model,
                    motor_id=motor.id,
                    data_name="Goal_Position",
                    value=pos
                )
                print(f"  [OK] {name} 写入成功")
                time.sleep(0.1)
            except Exception as e2:
                print(f"  [ERROR] {name} 写入失败: {e2}")

    # 再次读取位置验证
    print("\n[步骤4] 验证写入...")
    new_pos = robot.bus.sync_read("Present_Position")
    print(f"当前位置: {new_pos}")

    robot.disconnect()
    print("\n[INFO] 测试完成")

except Exception as e:
    print(f"\n[ERROR] 测试失败: {e}")
    import traceback
    traceback.print_exc()