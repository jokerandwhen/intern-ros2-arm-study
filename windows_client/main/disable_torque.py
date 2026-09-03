"""
禁用SoArm101扭矩，让机械臂可以手动移动
用于校准前的准备工作
"""

from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

# 配置
ROBOT_PORT = "COM3"
ROBOT_ID = "my_soarm101"

print("=" * 60)
print("SoArm101 扭矩禁用工具")
print("=" * 60)
print(f"串口: {ROBOT_PORT}")
print(f"ID: {ROBOT_ID}")
print("=" * 60)
print()

try:
    # 连接机械臂
    print("[INFO] 正在连接机械臂...")
    config = SOFollowerRobotConfig(port=ROBOT_PORT, id=ROBOT_ID)
    robot = SOFollower(config)
    robot.connect()
    print("[OK] 机械臂已连接")
    print()

    # 禁用所有关节的扭矩
    print("[INFO] 正在禁用所有关节扭矩...")
    print("[INFO] 禁用扭矩后，机械臂应该可以自由手动移动")
    print()

    # 遍历所有电机并禁用扭矩
    for motor_name in robot.bus.motors:
        motor_id = robot.bus.motors[motor_name]
        print(f"  禁用关节: {motor_name} (ID: {motor_id})")

        # 禁用扭矩（Torque = 0）
        robot.bus.write_with_motor_id(motor_id, "Torque_Enable", 0)

    print()
    print("[OK] 所有关节扭矩已禁用")
    print("[INFO] 现在可以手动移动机械臂了")
    print("[INFO] 请运行校准命令:")
    print(f"      lerobot-calibrate --robot.type=so101_follower --robot.port={ROBOT_PORT} --robot.id={ROBOT_ID}")
    print()

    # 保持连接，让用户确认
    input("按Enter键退出...")

    # 断开连接
    robot.disconnect()
    print("[INFO] 机械臂已断开")

except Exception as e:
    print(f"[ERROR] 错误: {e}")
    import traceback
    traceback.print_exc()