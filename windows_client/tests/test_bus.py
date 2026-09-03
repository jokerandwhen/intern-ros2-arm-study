"""测试舵机总线通信"""
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

print("="*60)
print("SoArm101 舵机总线测试")
print("="*60)

try:
    print("\n[步骤1] 连接到控制板...")
    config = SOFollowerRobotConfig(port="COM3")
    robot = SOFollower(config)
    robot.connect()
    print("[OK] 控制板连接成功")

    print("\n[步骤2] 检查舵机总线状态...")
    print(f"控制板类型: {type(robot.bus)}")

    # 尝试直接写入测试
    print("\n[步骤3] 尝试读取舵机位置...")

    # 测试每个舵机ID
    for motor_id in range(1, 7):
        try:
            # 使用底层API读取舵机位置
            if hasattr(robot.bus, 'read_with_motor_id'):
                pos = robot.bus.read_with_motor_id(
                    motor_model="sts3215",
                    motor_id=motor_id,
                    data_name="Present_Position"
                )
                print(f"  [OK] 舵机 {motor_id}: 位置={pos}")
            elif hasattr(robot.bus, 'sync_read'):
                # 尝试同步读取
                result = robot.bus.sync_read("Present_Position")
                print(f"  [OK] 同步读取成功: {result}")
                break
        except Exception as e:
            print(f"  [WARN] 舵机 {motor_id} 读取失败: {str(e)[:50]}")

    print("\n[步骤4] 检查控制板配置...")
    print(f"波特率: {robot.bus.port}")
    print(f"舵机配置: {list(robot.bus.motors.keys())}")

    # 尝试写入测试
    print("\n[步骤5] 尝试写入测试位置...")
    try:
        # 使用归一化值（0.0是中间位置）
        test_action = {
            "shoulder_pan": 0.0,
            "shoulder_lift": 0.0,
            "elbow_flex": 0.0,
            "wrist_flex": 0.0,
            "wrist_roll": 0.0,
            "gripper": 0.0
        }
        robot.send_action(test_action)
        print("[OK] 写入成功！舵机通信正常")
    except Exception as e:
        print(f"[ERROR] 写入失败: {e}")
        print("\n可能的原因：")
        print("  1. 舵机总线未连接到控制板")
        print("  2. 舵机ID设置不正确（应为1-6）")
        print("  3. 舵机波特率不匹配")

    robot.disconnect()
    print("\n[INFO] 测试完成")

except Exception as e:
    print(f"\n[ERROR] 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("如果所有舵机都读取失败，请检查：")
print("1. 舵机总线是否连接到控制板的'BUS'或'SERVO'接口")
print("2. 控制板上是否有独立的舵机电源接口（需要外部电源）")
print("3. 舵机是否为飞特(Feetech)品牌，型号STS3215")
print("="*60)