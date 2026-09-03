"""
诊断主臂夹爪读取问题
检查主臂夹爪是否能正确读取位置
"""

import time
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def diagnose_gripper():
    """诊断主臂夹爪"""

    print("="*70)
    print("主臂夹爪诊断工具")
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

        # 读取所有关节位置
        print("\n[步骤2] 读取所有关节位置...")
        obs = master.get_observation()

        print("\n主臂所有关节位置：")
        for joint, pos in obs.items():
            print(f"  {joint}: {pos:.2f}")

        # 重点检查夹爪
        gripper_pos = obs.get("gripper.pos", None)
        print(f"\n夹爪位置: {gripper_pos}")

        # 实时监控夹爪位置
        print("\n[步骤3] 实时监控夹爪位置...")
        print("请手动移动主臂夹爪，观察数值变化...")
        print("按 Ctrl+C 停止监控\n")

        last_gripper = gripper_pos
        frame = 0

        while True:
            obs = master.get_observation()
            current_gripper = obs.get("gripper.pos", 0)

            # 每秒打印一次
            if frame % 10 == 0:
                delta = current_gripper - last_gripper
                print(f"[帧{frame}] 夹爪: {current_gripper:.2f}° (变化: {delta:+.2f}°)")

            # 检测变化
            if abs(current_gripper - last_gripper) > 1.0:
                print(f"  ⚠️ 检测到夹爪移动！新位置: {current_gripper:.2f}°")
                last_gripper = current_gripper

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
    diagnose_gripper()