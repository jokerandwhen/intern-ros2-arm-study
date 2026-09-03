"""
解锁夹爪并测试控制功能
检查扭矩状态，禁用扭矩，测试夹爪控制
"""

import time
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def unlock_and_test_gripper():
    """解锁夹爪并测试"""

    print("="*70)
    print("解锁夹爪并测试控制功能")
    print("="*70)

    master = None
    try:
        # 连接主臂
        print("\n[步骤1] 连接主臂（COM3）...")
        master_config = SOFollowerRobotConfig(port="COM3")
        master = SOFollower(master_config)
        master.connect(calibrate=False)

        print("✓ 主臂连接成功")

        # 禁用所有扭矩（包括夹爪）
        print("\n[步骤2] 禁用所有扭矩...")
        master.bus.disable_torque()
        print("✓ 所有扭矩已禁用")

        # 检查夹爪位置
        print("\n[步骤3] 检查夹爪初始位置...")
        positions = master.bus.sync_read("Present_Position")
        gripper_pos = positions.get('gripper', 0)
        print(f"  夹爪初始位置: {gripper_pos:.2f}")

        # 现在应该可以手动移动夹爪了
        print("\n[步骤4] 手动测试...")
        print("现在应该可以手动移动夹爪了！")
        print("请尝试手动打开/关闭夹爪...")
        print("观察下面显示的位置是否变化...")
        print("按 Ctrl+C 停止测试\n")

        frame = 0
        last_pos = gripper_pos
        while True:
            positions = master.bus.sync_read("Present_Position")
            gripper_pos = positions.get('gripper', 0)

            # 每秒打印一次
            if frame % 10 == 0:
                print(f"[帧{frame}] 夹爪位置: {gripper_pos:.2f}")

            # 检测变化
            if abs(gripper_pos - last_pos) > 1.0:
                print(f"  ⚠️ 检测到夹爪移动！新位置: {gripper_pos:.2f}")
                last_pos = gripper_pos

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
    unlock_and_test_gripper()