"""
修复舵机电压上限寄存器（根治80%的12V闪灯问题）
按照官方文档，将 Max_Voltage_Limit 从 8V 改为 16V

步骤：
1. 确保12V电源已断开，只用USB 5V供电
2. 运行此脚本
3. 脚本会自动修改所有舵机的电压上限
4. 修改完成后，连接12V电源测试
"""

import time

def fix_voltage_limit():
    """修复舵机电压上限寄存器"""
    print("="*70)
    print("舵机电压上限寄存器修复工具")
    print("="*70)
    
    print("\n⚠️ 重要提示：")
    print("  1. 请确保使用 5V USB 供电（不要连接12V电源）")
    print("  2. 确保 USB 线已插入电脑")
    print("  3. 确保机械臂电源开关已打开")
    
    input("\n按 Enter 继续...")
    
    try:
        from lerobot.robots.so_follower.so_follower import SOFollower
        from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
        
        print("\n[步骤1] 连接从动臂...")
        # 尝试连接 COM3 或 COM4
        ports = ["COM3", "COM4"]
        master = None
        
        for port in ports:
            try:
                print(f"  尝试连接 {port}...")
                master_config = SOFollowerRobotConfig(port=port)
                master = SOFollower(master_config)
                master.connect(calibrate=False)
                print(f"  ✓ 成功连接 {port}")
                break
            except Exception as e:
                print(f"  ✗ {port} 连接失败: {e}")
                if master:
                    try:
                        master.disconnect()
                    except:
                        pass
                master = None
        
        if not master:
            print("\n❌ 无法连接任何端口！")
            print("请检查：")
            print("  1. USB 线是否已插入")
            print("  2. 设备管理器中查看正确的 COM 端口")
            return
        
        bus = master.bus
        
        # 舵机列表
        motors = {
            1: "shoulder_pan",
            2: "shoulder_lift",
            3: "elbow_flex",
            4: "wrist_flex",
            5: "wrist_roll",
            6: "gripper"
        }
        
        print("\n[步骤2] 读取当前电压上限...")
        for motor_id, motor_name in motors.items():
            try:
                # 尝试读取当前电压上限
                # 地址14：Max_Voltage_Limit
                current_limit = bus.read("Max_Voltage_Limit", motor_name, normalize=False)
                voltage = current_limit / 10.0  # 转换为伏特
                print(f"  电机 {motor_id} ({motor_name}): 当前上限 = {voltage:.1f}V")
                
                if voltage < 12.0:
                    print(f"    ⚠️ 电压上限过低！需要修改为 16.0V")
            except Exception as e:
                print(f"  电机 {motor_id} ({motor_name}): 读取失败 ({e})")
        
        print("\n[步骤3] 修改电压上限为 16.0V...")
        for motor_id, motor_name in motors.items():
            try:
                print(f"  正在修改电机 {motor_id} ({motor_name})...")
                
                # 步骤1: 解锁 EEPROM（地址55写0）
                try:
                    bus.write("Lock", 0, motor_name, normalize=False)
                except:
                    pass
                
                # 步骤2: 写入新的电压上限（地址14写160，代表16.0V）
                bus.write("Max_Voltage_Limit", 160, motor_name, normalize=False)
                
                # 步骤3: 锁定 EEPROM（地址55写1）
                try:
                    bus.write("Lock", 1, motor_name, normalize=False)
                except:
                    pass
                
                print(f"    ✓ 成功修改为 16.0V")
                
            except Exception as e:
                print(f"    ✗ 修改失败: {e}")
        
        print("\n[步骤4] 验证修改结果...")
        for motor_id, motor_name in motors.items():
            try:
                new_limit = bus.read("Max_Voltage_Limit", motor_name, normalize=False)
                voltage = new_limit / 10.0
                print(f"  电机 {motor_id} ({motor_name}): 新上限 = {voltage:.1f}V")
                
                if voltage >= 12.0:
                    print(f"    ✓ 修改成功！")
                else:
                    print(f"    ⚠️ 修改可能失败，请重试")
            except Exception as e:
                print(f"  电机 {motor_id} ({motor_name}): 验证失败 ({e})")
        
        master.disconnect()
        
        print("\n" + "="*70)
        print("修复完成！")
        print("="*70)
        
        print("\n下一步：")
        print("  1. 断开 USB 连接")
        print("  2. 连接 12V 电源适配器")
        print("  3. 打开机械臂电源开关")
        print("  4. 观察 LED 是否还闪烁")
        print("  5. 如果正常，运行 python full_diagnosis.py 测试")
        
    except Exception as e:
        print(f"\n❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_voltage_limit()