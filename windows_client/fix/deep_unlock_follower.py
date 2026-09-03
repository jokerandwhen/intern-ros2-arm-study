"""
深度解锁从动臂（COM3）的 EEPROM 限位
针对 shoulder_lift (电机2) 和 gripper (电机6)
"""

import time
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

config = SOFollowerRobotConfig(port="COM3", id="my_soarm101", use_degrees=True)
robot = SOFollower(config)

print("连接从动臂 COM3...")
robot.connect(calibrate=False)
time.sleep(1)

print("\n禁用扭矩...")
try:
    robot.bus.disable_torque()
    print("✓ 扭矩已禁用")
except Exception as e:
    print(f"⚠️ 禁用扭矩失败: {e}")

# 重点解锁电机2和6
print("\n深度解锁电机2(shoulder_lift)和电机6(gripper)...")

for motor_id in [2, 6]:
    print(f"\n=== 电机 {motor_id} ===")
    try:
        # 直接写入限位，不读取（因为读取API不支持）
        print("解锁EEPROM...")
        robot.bus.write(motor_id, 55, 0)
        time.sleep(0.05)

        print("写入新限位 [0, 4095]...")
        for attempt in range(3):
            robot.bus.write(motor_id, 11, 0)
            time.sleep(0.03)
            robot.bus.write(motor_id, 13, 4095)
            time.sleep(0.03)
            robot.bus.write(motor_id, 15, 1023)
            time.sleep(0.1)

        print("锁定EEPROM...")
        robot.bus.write(motor_id, 55, 1)
        time.sleep(0.1)

        print("✓ 写入完成")

    except Exception as e:
        print(f"❌ 电机{motor_id}解锁失败: {e}")
        import traceback
        traceback.print_exc()

print("\n测试电机能否移动到2048...")
try:
    robot.bus.enable_torque()
    print("✓ 扭矩已启用")
except Exception as e:
    print(f"⚠️ 启用扭矩失败: {e}")

# 尝试移动到2048
for motor_id in [2, 6]:
    motor_name = "shoulder_lift" if motor_id == 2 else "gripper"
    try:
        # 用正确的API读取位置
        current = robot.bus.read("Present_Position", motor_name, normalize=False)
        print(f"电机{motor_id}({motor_name})当前位置: {current}")
        # 慢慢移动到2048
        for i in range(10):
            target = int(current + (2048 - current) * (i+1) / 10)
            robot.bus.write(motor_id, 42, target)
            time.sleep(0.1)
        # 读取最终位置
        final = robot.bus.read("Present_Position", motor_name, normalize=False)
        print(f"电机{motor_id}移动后位置: {final}")
    except Exception as e:
        print(f"电机{motor_id}移动失败: {e}")

print("\n断开连接...")
robot.disconnect()
print("✓ 完成！请重新运行 sync.py")