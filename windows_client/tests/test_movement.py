"""直接控制机械臂测试"""
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
import time

print("="*60)
print("机械臂直接控制测试")
print("="*60)

try:
    print("\n[步骤1] 连接机械臂...")
    config = SOFollowerRobotConfig(port="COM3")
    robot = SOFollower(config)
    robot.connect()
    print("[OK] 连接成功")

    # 读取当前位置
    print("\n[步骤2] 读取当前位置...")
    current_pos = robot.bus.sync_read("Present_Position")
    print(f"当前位置: {current_pos}")

    # 测试：让机械臂移动到中间位置
    print("\n[步骤3] 移动到中间位置...")
    middle_position = {
        "shoulder_pan": 0.0,      # 底座：中间
        "shoulder_lift": 0.0,     # 肩部：中间
        "elbow_flex": 45.0,       # 肘部：弯曲45度
        "wrist_flex": 0.0,        # 手腕：中间
        "wrist_roll": 0.0,        # 手腕旋转：中间
        "gripper": 50.0           # 夹爪：半开
    }
    print(f"目标位置: {middle_position}")

    # 发送指令
    robot.bus.sync_write("Goal_Position", middle_position)
    print("[OK] 指令已发送，请观察机械臂是否移动...")

    # 等待移动完成
    time.sleep(2)

    # 再次读取位置验证
    print("\n[步骤4] 验证移动...")
    new_pos = robot.bus.sync_read("Present_Position")
    print(f"当前位置: {new_pos}")

    # 测试夹爪开合
    print("\n[步骤5] 测试夹爪开合...")
    for i in range(3):
        # 打开
        robot.bus.sync_write("Goal_Position", {**middle_position, "gripper": 100.0})
        print(f"  夹爪打开 (100)")
        time.sleep(1)

        # 关闭
        robot.bus.sync_write("Goal_Position", {**middle_position, "gripper": 0.0})
        print(f"  夹爪关闭 (0)")
        time.sleep(1)

    robot.disconnect()
    print("\n[OK] 测试完成")

except Exception as e:
    print(f"\n[ERROR] 测试失败: {e}")
    import traceback
    traceback.print_exc()