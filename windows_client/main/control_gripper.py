"""
主动控制夹爪到不同位置
测试夹爪是否能稳定控制
"""

import time
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def control_gripper():
    """控制夹爪"""

    print("="*70)
    print("主动控制夹爪测试")
    print("="*70)

    master = None
    try:
        # 连接主臂
        print("\n[步骤1] 连接主臂（COM3）...")
        master_config = SOFollowerRobotConfig(port="COM3")
        master = SOFollower(master_config)
        master.connect(calibrate=False)
        master.bus.disable_torque()

        print("✓ 主臂连接成功（扭矩已禁用）")

        # 测试不同的夹爪位置
        test_positions = [100, 75, 50, 25, 0, 50, 100]

        for target_pos in test_positions:
            print(f"\n[测试] 发送夹爪位置: {target_pos}")

            # 发送夹爪位置
            action = {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": 0.0,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": float(target_pos)
            }

            master.send_action(action)

            # 等待执行
            print(f"  等待执行...")
            time.sleep(1.0)

            # 读取实际位置
            positions = master.bus.sync_read("Present_Position")
            actual_pos = positions.get('gripper', 0)
            print(f"  目标位置: {target_pos}, 实际位置: {actual_pos:.2f}")

            # 检查是否达到目标
            if abs(actual_pos - target_pos) < 5.0:
                print(f"  ✓ 成功达到目标位置")
            else:
                print(f"  ⚠️ 位置偏差: {abs(actual_pos - target_pos):.2f}")

        # 实时监控夹爪
        print("\n" + "="*70)
        print("实时监控夹爪位置")
        print("="*70)
        print("观察夹爪位置是否稳定...")
        print("按 Ctrl+C 停止\n")

        frame = 0
        while True:
            positions = master.bus.sync_read("Present_Position")
            gripper_pos = positions.get('gripper', 0)

            if frame % 10 == 0:
                print(f"[帧{frame}] 夹爪位置: {gripper_pos:.2f}")

            frame += 1
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n[INFO] 测试已停止")

    except Exception as e:
        print(f"\n[错误] 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n[断开连接]")
        if master:
            try:
                master.disconnect()
            except:
                pass
        print("[OK] 测试完成")

if __name__ == "__main__":
    control_gripper()