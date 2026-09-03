"""
诊断夹爪电机的底层寄存器和状态
检查工作模式、限位、扭矩限制等
"""

import time
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def diagnose_gripper_registers():
    """诊断夹爪寄存器"""

    print("="*70)
    print("夹爪电机底层寄存器诊断")
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

        # 飞特 STS3215 常用寄存器地址：
        # 1. Mode (工作模式): 地址 33 (0x21), 长度 1 字节 (0: 位置模式, 1: 恒速模式, 2: 顺从模式, 3: 步进模式)
        # 2. Torque_Limit (最大扭矩限制): 地址 16 (0x10), 长度 2 字节
        # 3. Min_Position_Limit (最小位置限制): 地址 9 (0x09), 长度 2 字节
        # 4. Max_Position_Limit (最大位置限制): 地址 11 (0x0B), 长度 2 字节
        # 5. Torque_Enable (扭矩使能): 地址 40 (0x28), 长度 1 字节
        # 6. Present_Position (当前位置): 地址 56 (0x38), 长度 2 字节
        # 7. Goal_Position (目标位置): 地址 42 (0x2A), 长度 2 字节

        print("\n[步骤2] 读取夹爪电机 (ID=6) 的底层寄存器...")
        
        # 尝试读取工作模式
        try:
            mode = bus.read("Mode", "gripper", normalize=False)
            print(f"  工作模式 (Mode): {mode} (0:位置模式, 1:恒速, 2:顺从, 3:步进)")
        except Exception as e:
            print(f"  Mode 读取失败: {e}")

        # 尝试读取最大扭矩限制
        try:
            torque_limit = bus.read("Torque_Limit", "gripper", normalize=False)
            print(f"  最大扭矩限制 (Torque_Limit): {torque_limit} (0-1023)")
        except Exception as e:
            print(f"  Torque_Limit 读取失败: {e}")

        # 尝试读取位置限制
        try:
            min_pos = bus.read("Min_Position_Limit", "gripper", normalize=False)
            max_pos = bus.read("Max_Position_Limit", "gripper", normalize=False)
            print(f"  物理限位: 最小 = {min_pos}, 最大 = {max_pos} (0-4095)")
        except Exception as e:
            print(f"  位置限制读取失败: {e}")

        # 尝试读取当前电压和温度
        try:
            voltage = bus.read("Present_Voltage", "gripper", normalize=False)
            temp = bus.read("Present_Temperature", "gripper", normalize=False)
            print(f"  当前电压: {voltage/10.0:.1f}V, 温度: {temp}°C")
        except Exception as e:
            print(f"  电压/温度读取失败: {e}")

        # 3. 尝试修改限位和模式（如果被限制了）
        print("\n[步骤3] 尝试解除可能的软件限制...")
        try:
            # 确保是位置模式 (0)
            print("  设置工作模式为位置模式 (0)...")
            bus.write("Mode", 0, "gripper", normalize=False)
            
            # 设置最大扭矩限制为最大值 (1023)
            print("  设置最大扭矩限制为 1023...")
            bus.write("Torque_Limit", 1023, "gripper", normalize=False)
            
            # 设置限位为最大范围 (0-4095)
            print("  设置物理限位为最大范围 (0-4095)...")
            bus.write("Min_Position_Limit", 0, "gripper", normalize=False)
            bus.write("Max_Position_Limit", 4095, "gripper", normalize=False)
            
            print("  ✓ 限制已解除")
        except Exception as e:
            print(f"  ⚠️ 解除限制失败: {e}")

        # 4. 重新测试控制
        print("\n[步骤4] 重新测试控制...")
        try:
            bus.enable_torque()
            
            # 目标位置
            targets = [2048, 1800, 1600, 2048]
            for target in targets:
                print(f"\n  写入目标位置: {target}")
                bus.sync_write("Goal_Position", {"gripper": target}, normalize=False)
                time.sleep(1.0)
                
                actual = bus.read("Present_Position", "gripper", normalize=False)
                print(f"    实际位置: {actual}")
                
        except Exception as e:
            print(f"  控制测试失败: {e}")
            
        bus.disable_torque()

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
    diagnose_gripper_registers()