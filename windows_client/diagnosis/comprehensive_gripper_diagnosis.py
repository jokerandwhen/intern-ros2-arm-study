"""
全面诊断夹爪电机
从底层检查所有寄存器和状态
"""

import time
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def comprehensive_gripper_diagnosis():
    """全面诊断夹爪"""

    print("="*70)
    print("夹爪电机全面诊断")
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

        # 1. 检查夹爪电机配置
        print("\n[步骤2] 检查夹爪电机配置...")
        if 'gripper' in master.bus.motors:
            gripper_config = master.bus.motors['gripper']
            print(f"  夹爪电机ID: {gripper_config.id}")
            print(f"  夹爪电机型号: {gripper_config.model}")
            print(f"  norm_mode: {gripper_config.norm_mode}")

        # 2. 读取所有寄存器
        print("\n[步骤3] 读取夹爪电机所有寄存器...")
        try:
            print("  尝试读取Present_Position...")
            positions = master.bus.sync_read("Present_Position")
            print(f"    Present_Position: {positions.get('gripper', 'N/A')}")
        except Exception as e:
            print(f"    Present_Position读取失败: {e}")

        try:
            print("  尝试读取Present_Load...")
            loads = master.bus.sync_read("Present_Load")
            print(f"    Present_Load: {loads.get('gripper', 'N/A')}")
        except Exception as e:
            print(f"    Present_Load读取失败: {e}")

        try:
            print("  尝试读取Present_Voltage...")
            voltages = master.bus.sync_read("Present_Voltage")
            print(f"    Present_Voltage: {voltages.get('gripper', 'N/A')}")
        except Exception as e:
            print(f"    Present_Voltage读取失败: {e}")

        try:
            print("  尝试读取Present_Temperature...")
            temps = master.bus.sync_read("Present_Temperature")
            print(f"    Present_Temperature: {temps.get('gripper', 'N/A')}")
        except Exception as e:
            print(f"    Present_Temperature读取失败: {e}")

        # 3. 检查扭矩状态
        print("\n[步骤4] 检查扭矩状态...")
        try:
            # 尝试读取扭矩使能状态
            print("  检查Torque_Enable...")
            # 尝试不同的寄存器名称
            torque_names = ["Torque_Enable", "Torque", "Enable"]
            for name in torque_names:
                try:
                    torque_status = master.bus.sync_read(name)
                    print(f"    {name}: {torque_status}")
                    break
                except:
                    continue
        except Exception as e:
            print(f"  ⚠️ 无法读取扭矩状态: {e}")

        # 4. 尝试手动写入位置
        print("\n[步骤5] 尝试手动写入位置...")
        test_values = [180, 150, 100, 50, 0]

        for value in test_values:
            print(f"\n  测试写入位置: {value}")

            # 方法1：使用sync_write
            try:
                print("    方法1: 使用sync_write...")
                master.bus.sync_write("Goal_Position", {"gripper": float(value)})
                time.sleep(0.5)

                # 读取实际位置
                positions = master.bus.sync_read("Present_Position")
                actual = positions.get('gripper', 'N/A')
                print(f"      目标: {value}, 实际: {actual}")
            except Exception as e:
                print(f"      sync_write失败: {e}")

            # 方法2：使用send_action（只控制夹爪）
            try:
                print("    方法2: 使用send_action（只控制夹爪）...")

                # 先读取当前所有关节位置
                current_positions = master.bus.sync_read("Present_Position")

                # 构造action，保持其他关节不变，只改变夹爪
                action = {
                    "shoulder_pan.pos": current_positions.get('shoulder_pan', 0.0),
                    "shoulder_lift.pos": current_positions.get('shoulder_lift', 0.0),
                    "elbow_flex.pos": current_positions.get('elbow_flex', 0.0),
                    "wrist_flex.pos": current_positions.get('wrist_flex', 0.0),
                    "wrist_roll.pos": current_positions.get('wrist_roll', 0.0),
                    "gripper.pos": float(value)  # 只改变夹爪
                }
                master.send_action(action)
                time.sleep(0.5)

                # 读取实际位置
                positions = master.bus.sync_read("Present_Position")
                actual = positions.get('gripper', 'N/A')
                print(f"      目标: {value}, 实际: {actual}")
            except Exception as e:
                print(f"      send_action失败: {e}")

        # 5. 检查是否有硬件限制
        print("\n[步骤6] 检查硬件限制...")
        print("  请手动移动夹爪，观察位置变化...")
        print("  按Ctrl+C停止监控\n")

        frame = 0
        positions_history = []
        while frame < 50:  # 监控5秒
            positions = master.bus.sync_read("Present_Position")
            gripper_pos = positions.get('gripper', 0)

            if frame % 10 == 0:
                print(f"[帧{frame}] 夹爪位置: {gripper_pos:.2f}")

            positions_history.append(gripper_pos)
            frame += 1
            time.sleep(0.1)

        # 分析位置变化
        print("\n[步骤7] 分析位置历史...")
        if len(positions_history) > 0:
            min_pos = min(positions_history)
            max_pos = max(positions_history)
            avg_pos = sum(positions_history) / len(positions_history)

            print(f"  最小位置: {min_pos:.2f}")
            print(f"  最大位置: {max_pos:.2f}")
            print(f"  平均位置: {avg_pos:.2f}")
            print(f"  位置变化: {max_pos - min_pos:.2f}")

            if max_pos - min_pos < 1.0:
                print("  ⚠️ 位置几乎无变化，可能原因：")
                print("    1. 夹爪电机硬件故障")
                print("    2. 夹爪电机被锁定")
                print("    3. 夹爪电机配置错误")
            else:
                print("  ✓ 位置有变化，但无法控制")

        # 6. 最终建议
        print("\n" + "="*70)
        print("诊断结论")
        print("="*70)
        print("如果位置一直显示100且无法控制，可能的原因：")
        print("  1. 夹爪电机硬件故障")
        print("  2. 夹爪电机固件问题")
        print("  3. 夹爪电机需要重新校准")
        print("\n建议：")
        print("  1. 尝试断电重启机械臂")
        print("  2. 检查夹爪电机线缆连接")
        print("  3. 联系厂商技术支持")

    except KeyboardInterrupt:
        print("\n\n[INFO] 诊断已停止")

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
    comprehensive_gripper_diagnosis()