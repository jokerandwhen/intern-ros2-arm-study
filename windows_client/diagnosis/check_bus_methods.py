"""
检查主臂夹爪电机配置
查看bus对象的可用方法和属性
"""

import time
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def check_bus_methods():
    """检查bus对象的方法"""

    print("="*70)
    print("检查主臂夹爪电机配置")
    print("="*70)

    master = None
    try:
        # 连接主臂
        print("\n[步骤1] 连接主臂（COM3）...")
        master_config = SOFollowerRobotConfig(port="COM3")
        master = SOFollower(master_config)
        master.connect(calibrate=False)

        print("✓ 主臂连接成功")

        # 检查bus对象的属性和方法
        print("\n[步骤2] 检查bus对象的可用方法...")
        bus_attrs = [attr for attr in dir(master.bus) if not attr.startswith('_')]
        print(f"  可用方法/属性: {bus_attrs[:10]}...")  # 只显示前10个

        # 检查是否有motors字典
        if hasattr(master.bus, 'motors'):
            print(f"\n[步骤3] 检查motors字典...")
            print(f"  motors类型: {type(master.bus.motors)}")
            if isinstance(master.bus.motors, dict):
                print(f"  motors内容: {master.bus.motors}")

        # 检查motor_names
        if hasattr(master.bus, 'motor_names'):
            print(f"\n[步骤4] 检查motor_names...")
            print(f"  motor_names: {master.bus.motor_names}")

        # 检查motor_ids
        if hasattr(master.bus, 'motor_ids'):
            print(f"\n[步骤5] 检查motor_ids...")
            print(f"  motor_ids: {master.bus.motor_ids}")

        # 尝试读取所有电机
        print("\n[步骤6] 尝试读取所有电机...")
        if hasattr(master.bus, 'motor_names'):
            for motor_name in master.bus.motor_names:
                try:
                    # 尝试使用 motor_name 读取
                    pos_dict = master.bus.read("Present_Position")
                    if motor_name in pos_dict:
                        print(f"  {motor_name}: {pos_dict[motor_name]:.2f}")
                except Exception as e:
                    print(f"  {motor_name}: 读取失败 ({e})")

        # 再次读取observation
        print("\n[步骤7] 读取完整的observation...")
        obs = master.get_observation()
        for joint, pos in obs.items():
            print(f"  {joint}: {pos:.2f}")

        # 重点检查夹爪
        print("\n[步骤8] 检查夹爪配置...")
        if 'gripper.pos' in obs:
            print(f"  gripper.pos: {obs['gripper.pos']}")
        else:
            print("  ⚠️ gripper.pos 不在 observation 中！")

        # 检查是否有 gripper 配置
        if hasattr(master.bus, 'motors') and isinstance(master.bus.motors, dict):
            if 'gripper' in master.bus.motors:
                print(f"  ✓ gripper 在 motors 字典中")
                print(f"  gripper配置: {master.bus.motors['gripper']}")
            else:
                print(f"  ⚠️ gripper 不在 motors 字典中！")
                print(f"  可用的motors: {list(master.bus.motors.keys())}")

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
    check_bus_methods()