"""
测试从动臂（COM3）各关节的真实可动范围
"""

import time
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

MOTORS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]

config = SOFollowerRobotConfig(port="COM3", id="my_soarm101", use_degrees=True)
robot = SOFollower(config)

print("连接从动臂 COM3...")
robot.connect(calibrate=False)
time.sleep(1)

print("\n读取当前状态...")
for motor in MOTORS:
    try:
        pos = robot.bus.read("Present_Position", motor, normalize=False)
        print(f"  {motor}: 当前位置={pos}")
    except Exception as e:
        print(f"  {motor}: 读取失败 {e}")

print("\n读取当前限位...")
for i, motor in enumerate(MOTORS, 1):
    try:
        min_limit = robot.bus.read(i, 11, 2)
        max_limit = robot.bus.read(i, 13, 2)
        max_torque = robot.bus.read(i, 15, 2)
        print(f"  {motor}(ID={i}): 限位=[{min_limit}, {max_limit}] 最大扭矩={max_torque}")
    except Exception as e:
        print(f"  {motor}(ID={i}): 读取失败 {e}")

print("\n测试各关节移动到中间位置 2048...")
try:
    robot.bus.enable_torque()
    print("✓ 扭矩已启用")
except Exception as e:
    print(f"⚠️ 启用扭矩失败: {e}")

# 逐步移动到2048
print("\n  移动到 2048...")
for step in range(1, 11):
    target = {}
    for i, motor in enumerate(MOTORS, 1):
        try:
            current = robot.bus.read("Present_Position", motor, normalize=False)
            t = int(current + (2048 - current) * step / 10)
            target[motor] = max(0, min(4095, t))
        except:
            target[motor] = 2048
    try:
        robot.bus.sync_write("Goal_Position", target, normalize=False)
    except Exception as e:
        print(f"  移动失败: {e}")
    time.sleep(0.2)

time.sleep(1)
print("\n移动后位置：")
for motor in MOTORS:
    try:
        pos = robot.bus.read("Present_Position", motor, normalize=False)
        print(f"  {motor}: 位置={pos}")
    except Exception as e:
        print(f"  {motor}: 读取失败 {e}")

print("\n断开连接...")
robot.disconnect()
print("完成")
