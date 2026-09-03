"""
安全诊断程序 - 不进行任何初始化运动
只读取机械臂当前状态，用于诊断问题
"""

import time
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

print("="*70)
print("安全诊断程序 - 不进行任何初始化运动")
print("="*70)
print("\n⚠️ 此程序只读取状态，不会移动机械臂")

# 安全参数
MASTER_PORT = "COM3"
PUPPET_PORT = "COM4"

master = None
puppet = None

try:
    # 1. 连接主臂（不进行任何初始化）
    print(f"\n[步骤1] 连接主臂（{MASTER_PORT}）...")
    master_config = SOFollowerRobotConfig(port=MASTER_PORT)
    master = SOFollower(master_config)

    # 关键：使用 calibrate=False 避免任何初始化运动
    master.connect(calibrate=False)

    # 立即禁用扭矩，确保舵机不会移动
    master.bus.disable_torque()
    print("✓ 主臂连接成功（扭矩已禁用，舵机不会移动）")

    # 2. 连接辅助臂（不进行任何初始化）
    print(f"\n[步骤2] 连接辅助臂（{PUPPET_PORT}）...")
    puppet_config = SOFollowerRobotConfig(port=PUPPET_PORT)
    puppet = SOFollower(puppet_config)

    # 关键：使用 calibrate=False 避免任何初始化运动
    puppet.connect(calibrate=False)

    # 立即禁用扭矩
    puppet.bus.disable_torque()
    print("✓ 辅助臂连接成功（扭矩已禁用，舵机不会移动）")

    # 3. 读取当前位置（只读，不移动）
    print("\n" + "="*70)
    print("当前位置读取（只读，不移动）")
    print("="*70)

    master_obs = master.get_observation()
    puppet_obs = puppet.get_observation()

    print("\n主臂（COM3）当前位置：")
    for joint, pos in master_obs.items():
        status = "⚠️ 超限" if abs(pos) > 150 else "✓ 正常"
        print(f"  {joint}: {pos:7.2f}° {status}")

    print("\n辅助臂（COM4）当前位置：")
    for joint, pos in puppet_obs.items():
        status = "⚠️ 超限" if abs(pos) > 150 else "✓ 正常"
        print(f"  {joint}: {pos:7.2f}° {status}")

    # 4. 安全限幅检查
    print("\n" + "="*70)
    print("安全限幅检查")
    print("="*70)

    joints_to_check = ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos"]

    for joint in joints_to_check:
        master_pos = master_obs.get(joint, 0)
        puppet_pos = puppet_obs.get(joint, 0)

        if abs(master_pos) > 160:
            print(f"⚠️ 主臂 {joint} 超出安全范围：{master_pos:.2f}°")
        if abs(puppet_pos) > 160:
            print(f"⚠️ 辅助臂 {joint} 超出安全范围：{puppet_pos:.2f}°")

    print("\n✓ 诊断完成，机械臂保持当前位置（扭矩已禁用）")
    print("\n如果位置超出范围，请：")
    print("  1. 小心手动移动机械臂到中间位置")
    print("  2. 确认所有关节角度在 ±150° 范围内")
    print("  3. 再次运行此程序验证")

except KeyboardInterrupt:
    print("\n\n[INFO] 用户中断")

except Exception as e:
    print(f"\n[错误] 诊断失败: {e}")
    import traceback
    traceba