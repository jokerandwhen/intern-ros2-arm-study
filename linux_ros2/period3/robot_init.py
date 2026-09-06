"""机械臂初始化控制"""
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
import time

print("=" * 60)
print("机械臂初始化程序")
print("=" * 60)

# 关节名称和限制
JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
JOINT_MIN = [-180.0, -90.0, -135.0, -90.0, -180.0, 0.0]
JOINT_MAX = [180.0, 90.0, 135.0, 90.0, 180.0, 100.0]

try:
    # 步骤1: 连接机械臂
    print("\n[步骤1] 连接机械臂...")
    config = SOFollowerRobotConfig(port="/dev/ttyACM0")
    robot = SOFollower(config)
    robot.connect()
    print("[OK] 连接成功")

    # 步骤2: 读取当前位置
    print("\n[步骤2] 读取当前位置...")
    current_pos = robot.bus.sync_read("Present_Position")
    for name, pos in current_pos.items():
        print(f"  {name}: {pos:.1f}°")

    # 步骤3: 设置安全初始位置（逐步移动，避免过载）
    print("\n[步骤3] 逐步移动到初始位置...")
    
    # 先读取当前位置
    current_pos = robot.bus.sync_read("Present_Position")
    
    # 逐步移动每个关节，避免大角度跳变
    init_angles = {
        "shoulder_pan": 0.0,      # 底座：0度
        "shoulder_lift": -30.0,  # 肩部：-30度
        "elbow_flex": 20.0,      # 肘部：先移动到小角度（原来是60度太大了）
        "wrist_flex": 0.0,       # 腕部1：0度
        "wrist_roll": 0.0,       # 腕部2：0度
        "gripper": 50.0          # 夹爪：50度（半开）
    }

    print(f"第一步目标位置: {init_angles}")
    robot.bus.sync_write("Goal_Position", init_angles)
    print("[OK] 等待机械臂移动...")
    time.sleep(2)
    
    # 检查是否有舵机触发了过载
    print("\n检查舵机状态...")
    try:
        final_pos = robot.bus.sync_read("Present_Position")
        for name, pos in final_pos.items():
            print(f"  {name}: {pos:.1f}°")
    except Exception as e:
        print(f"  [WARN] 读取状态时出错: {e}")
    
    # 如果 elbow 正常，再移动到目标角度
    print("\n尝试移动 elbow 到目标角度...")
    try:
        current_elbow = robot.bus.read("Present_Position", "elbow_flex")
        print(f"  elbow 当前位置: {current_elbow:.1f}°")
        
        # 逐步增加角度
        for target in [20, 40, 60]:
            print(f"  尝试移动到 {target}°...")
            robot.bus.write("Goal_Position", "elbow_flex", float(target))
            time.sleep(1.5)
            try:
                pos = robot.bus.read("Present_Position", "elbow_flex")
                print(f"    实际位置: {pos:.1f}°")
            except Exception as e:
                print(f"    [WARN] {e}")
                break
    except Exception as e:
        print(f"  [WARN] elbow 移动失败: {e}")
        print("  [INFO] elbow 可能处于过载状态，跳过此关节")

    # 等待机械臂到达目标位置
    time.sleep(3)

    # 步骤4: 验证当前位置
    print("\n[步骤4] 验证当前位置...")
    final_pos = robot.bus.sync_read("Present_Position")
    for name, pos in final_pos.items():
        target = init_angles[name]
        diff = abs(pos - target)
        status = "✓" if diff < 2.0 else "✗"
        print(f"  {name}: {pos:.1f}° (目标: {target:.1f}°) {status}")

    print("\n[OK] 初始化完成！")

    # 断开连接
    print("\n[INFO] 断开连接...")
    robot.disconnect()
    print("[OK] 程序退出")

except Exception as e:
    print(f"\n[ERROR] 初始化失败: {e}")
    import traceback
    traceback.print_exc()