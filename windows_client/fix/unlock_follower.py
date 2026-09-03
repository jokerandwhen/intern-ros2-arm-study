"""
解除从动臂（COM3）所有电机的EEPROM限位
让 shoulder_lift 和 gripper 能使用完整 0-4095 范围
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

print("\n读取当前限位...")
for motor_id in [2, 6]:  # 重点解锁 shoulder_lift 和 gripper
    try:
        min_limit = robot.bus.read(motor_id, 11, 2)
        max_limit = robot.bus.read(motor_id, 13, 2)
        max_torque = robot.bus.read(motor_id, 15, 2)
        print(f"  电机{motor_id}: 限位=[{min_limit}, {max_limit}] 最大扭矩={max_torque}")
    except Exception as e:
        print(f"  电机{motor_id}: 读取失败 {e}")

print("\n解锁EEPROM并写入新限位...")
for motor_id in range(1, 7):
    try:
        # 解锁EEPROM（地址55写0）
        robot.bus.write(motor_id, 55, 0)
        time.sleep(0.01)
        # 写入最小限位=0
        robot.bus.write(motor_id, 11, 0)
        time.sleep(0.01)
        # 写入最大限位=4095
        robot.bus.write(motor_id, 13, 4095)
        time.sleep(0.01)
        # 最大扭矩=1023
        robot.bus.write(motor_id, 15, 1023)
        time.sleep(0.01)
        # 锁定EEPROM（地址55写1）
        robot.bus.write(motor_id, 55, 1)
        time.sleep(0.01)
        print(f"✓ 电机{motor_id} 已解锁并重新锁定")
    except Exception as e:
        print(f"⚠️ 电机{motor_id} 解锁失败: {e}")

print("\n验证新限位...")
for motor_id in [2, 6]:
    try:
        min_limit = robot.bus.read(motor_id, 11, 2)
        max_limit = robot.bus.read(motor_id, 13, 2)
        max_torque = robot.bus.read(motor_id, 15, 2)
        print(f"  电机{motor_id}: 限位=[{min_limit}, {max_limit}] 最大扭矩={max_torque}")
    except Exception as e:
        print(f"  电机{motor_id}: 读取失败 {e}")

print("\n断开连接...")
robot.disconnect()
print("✓ 完成！请重新运行 sync.py")
