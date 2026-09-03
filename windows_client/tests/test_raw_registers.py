"""
直接读写舵机原始寄存器（0-4095）- 修复写入方法
使用底层 write_with_motor_id 或 write 寄存器
"""

import time
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def test_raw_registers_fixed():
    """测试原始寄存器读写"""

    print("="*70)
    print("舵机原始寄存器读写测试 (0-4095) - 修复版")
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

        bus = master.bus

        # 1. 读取所有电机的原始位置 (0-4095)
        print("\n[步骤2] 读取所有电机的原始位置 (0-4095)...")
        motor_ids = {
            "shoulder_pan": 1,
            "shoulder_lift": 2,
            "elbow_flex": 3,
            "wrist_flex": 4,
            "wrist_roll": 5,
            "gripper": 6
        }

        raw_positions = {}
        for name, motor_id in motor_ids.items():
            try:
                raw_pos = bus.read("Present_Position", name, normalize=False)
                raw_positions[name] = raw_pos
                print(f"  {name} (ID={motor_id}): 原始值 = {raw_pos}")
            except Exception as e:
                print(f"  {name} (ID={motor_id}): 读取失败 ({e})")

        # 2. 重点测试夹爪电机 (ID=6)
        print("\n[步骤3] 重点测试夹爪电机 (ID=6)...")
        try:
            raw_gripper = raw_positions.get("gripper", 2048)
            print(f"  当前夹爪原始位置: {raw_gripper}")

            # 启用主臂扭矩以进行控制测试
            print("\n  启用主臂扭矩以进行控制测试...")
            bus.enable_torque()

            # 尝试写入当前位置附近的值，避免剧烈运动
            # 飞特舵机 0-4095 范围
            test_targets = [int(raw_gripper)]
            if raw_gripper > 2000:
                test_targets.extend([int(raw_gripper) - 200, int(raw_gripper) - 400, int(raw_gripper)])
            else:
                test_targets.extend([int(raw_gripper) + 200, int(raw_gripper) + 400, int(raw_gripper)])

            for target in test_targets:
                print(f"\n  尝试写入夹爪目标原始值: {target}")
                
                # 尝试使用底层 write_with_motor_id 写入
                try:
                    print("    尝试使用 write_with_motor_id...")
                    bus.write_with_motor_id(
                        motor_model="sts3215",
                        motor_id=6,
                        data_name="Goal_Position",
                        value=target
                    )
                    print("      ✓ 写入成功")
                except Exception as e_write:
                    print(f"      ⚠️ write_with_motor_id 失败: {e_write}")
                    
                    # 尝试使用 sync_write 写入原始值
                    try:
                        print("    尝试使用 sync_write...")
                        bus.sync_write("Goal_Position", {"gripper": target}, normalize=False)
                        print("      ✓ sync_write 写入成功")
                    except Exception as e_sync:
                        print(f"      ⚠️ sync_write 失败: {e_sync}")

                time.sleep(1.0)

                # 读取实际位置
                try:
                    actual = bus.read("Present_Position", "gripper", normalize=False)
                    print(f"    目标: {target}, 实际: {actual}")
                except Exception as e_read:
                    print(f"    读取实际位置失败: {e_read}")

        except Exception as e:
            print(f"  ❌ 夹爪原始读写测试失败: {e}")

        # 4. 禁用扭矩
        bus.disable_torque()

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
    test_raw_registers_fixed()