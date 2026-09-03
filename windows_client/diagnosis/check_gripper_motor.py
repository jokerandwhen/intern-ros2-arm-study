"""
直接读取主臂夹爪电机位置
绕过高层API，直接读取电机寄存器
"""

import time
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def check_gripper_motor_direct():
    """直接读取夹爪电机"""

    print("="*70)
    print("直接读取主臂夹爪电机")
    print("="*70)

    master = None
    try:
        # 连接主臂
        print("\n[步骤1] 连接主臂（COM3）...")
        master_config = SOFollowerRobotConfig(port="COM3")
        master = SOFollower(master_config)
        master.connect(calibrate=False)

        print("✓ 主臂连接成功")

        # 尝试直接读取总线上的所有电机
        print("\n[步骤2] 读取所有电机位置...")

        # SoArm101的电机ID通常是1-6
        # 1: shoulder_pan
        # 2: shoulder_lift
        # 3: elbow_flex
        # 4: wrist_flex
        # 5: wrist_roll
        # 6: gripper

        motor_ids = [1, 2, 3, 4, 5, 6]

        print("\n直接读取电机位置：")
        for motor_id in motor_ids:
            try:
                # 尝试读取电机位置
                pos = master.bus.read_with_motor_id(motor_id, "Present_Position")
                print(f"  电机 {motor_id}: {pos:.2f}")
            except Exception as e:
                print(f"  电机 {motor_id}: 读取失败 ({e})")

        # 重点检查电机6（夹爪）
        print("\n[步骤3] 重点检查夹爪电机（ID=6）...")
        try:
            # 尝试多种方式读取
            print("  尝试读取 Present_Position...")
            pos1 = master.bus.read_with_motor_id(6, "Present_Position")
            print(f"  Present_Position: {pos1:.2f}")

            print("  尝试读取 Present_Load...")
            load = master.bus.read_with_motor_id(6, "Present_Load")
            print(f"  Present_Load: {load:.2f}")

            print("  尝试读取 Present_Temperature...")
            temp = master.bus.read_with_motor_id(6, "Present_Temperature")
            print(f"  Present_Temperature: {temp:.2f}")

        except Exception as e:
            print(f"  ❌ 夹爪电机读取失败: {e}")

        # 实时监控电机6
        print("\n[步骤4] 实时监控夹爪电机...")
        print("请手动移动主臂夹爪...")
        print("按 Ctrl+C 停止\n")

        frame = 0
        while True:
            try:
                pos = master.bus.read_with_motor_id(6, "Present_Position")
                if frame % 10 == 0:
                    print(f"[帧{frame}] 夹爪电机位置: {pos:.2f}")
            except Exception as e:
                print(f"[帧{frame}] 读取失败: {e}")

            frame += 1
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n[INFO] 监控已停止")

    except Exception as e:
        print(f"\n[错误] 诊断失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n[断开连接]")
        if master:
            try:
                master.disconnect()
            except:
                pass
        print("[OK] 诊断完成")

if __name__ == "__main__":
    check_gripper_motor_direct()