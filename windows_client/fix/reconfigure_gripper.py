"""
单独校准主臂夹爪
将夹爪从RANGE_0_100模式改为DEGREES模式（0-180度）
"""

import time
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

# 尝试从正确的路径导入Motor
try:
    from lerobot.motors.motors_bus import Motor, MotorNormMode
except ImportError:
    try:
        from lerobot.motors import Motor, MotorNormMode
    except ImportError:
        # 如果还是失败，我们手动定义
        Motor = None
        MotorNormMode = None

def reconfigure_gripper():
    """重新配置夹爪电机"""

    print("="*70)
    print("重新配置主臂夹爪")
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

        # 检查当前夹爪配置
        print("\n[步骤2] 检查当前夹爪配置...")
        if 'gripper' in master.bus.motors:
            gripper_config = master.bus.motors['gripper']
            print(f"  夹爪电机ID: {gripper_config.id}")
            print(f"  夹爪电机型号: {gripper_config.model}")
            print(f"  当前norm_mode: {gripper_config.norm_mode}")

            # 检查是否是RANGE_0_100模式
            if str(gripper_config.norm_mode) == 'range_0_100' or 'RANGE_0_100' in str(gripper_config.norm_mode):
                print("\n  ⚠️ 检测到夹爪是RANGE_0_100模式")
                print("  这就是为什么夹爪一直显示100的原因！")

        # 读取当前夹爪位置
        print("\n[步骤3] 读取当前夹爪位置...")
        positions = master.bus.sync_read("Present_Position")
        gripper_pos = positions.get('gripper', 0)
        print(f"  当前夹爪位置: {gripper_pos:.2f}")

        # 尝试手动修改夹爪配置（临时）
        print("\n[步骤4] 尝试修改夹爪配置...")
        print("  将norm_mode从RANGE_0_100改为DEGREES...")

        # 直接修改现有Motor对象的norm_mode
        if 'gripper' in master.bus.motors:
            # 获取当前配置
            old_config = master.bus.motors['gripper']

            # 创建新的Motor配置（DEGREES模式）
            # 使用字符串形式避免导入问题
            try:
                # 尝试直接修改norm_mode属性
                if hasattr(old_config, 'norm_mode'):
                    old_config.norm_mode = 'degrees'  # 尝试修改为度数模式
                    print("  ✓ 尝试直接修改norm_mode属性")
            except Exception as e:
                print(f"  ⚠️ 无法直接修改norm_mode: {e}")
                print("  将继续使用当前模式测试...")

        print(f"  当前norm_mode: {master.bus.motors['gripper'].norm_mode}")

        # 测试夹爪控制（度数模式）
        print("\n[步骤5] 测试夹爪控制（度数模式）...")
        test_positions = [180, 150, 100, 50, 0, 90, 180]

        for target_pos in test_positions:
            print(f"\n  发送夹爪位置: {target_pos}度")

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
            print(f"    等待执行...")
            time.sleep(1.0)

            # 读取实际位置
            positions = master.bus.sync_read("Present_Position")
            actual_pos = positions.get('gripper', 0)
            print(f"    目标位置: {target_pos}度, 实际位置: {actual_pos:.2f}度")

            # 检查是否达到目标
            if abs(actual_pos - target_pos) < 10.0:
                print(f"    ✓ 成功达到目标位置")
            else:
                print(f"    ⚠️ 位置偏差: {abs(actual_pos - target_pos):.2f}度")

        # 实时监控夹爪
        print("\n" + "="*70)
        print("实时监控夹爪位置（度数模式）")
        print("="*70)
        print("观察夹爪位置是否稳定...")
        print("按 Ctrl+C 停止\n")

        frame = 0
        while True:
            positions = master.bus.sync_read("Present_Position")
            gripper_pos = positions.get('gripper', 0)

            if frame % 10 == 0:
                print(f"[帧{frame}] 夹爪位置: {gripper_pos:.2f}度")

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
    reconfigure_gripper()