"""
清除舵机故障锁存
按照官方文档，清除所有舵机的保护标志

步骤：
1. 连接机械臂（5V或12V都可以）
2. 运行此脚本
3. 脚本会自动清除所有舵机的故障锁存
"""

import time

def clear_faults():
    """清除舵机故障锁存"""
    print("="*70)
    print("舵机故障清除工具")
    print("="*70)
    
    print("\n说明：")
    print("  这个脚本会清除所有舵机的故障锁存（电压报错、过流报错等）")
    print("  如果你的舵机LED闪烁，运行这个脚本可能可以解决问题")
    
    input("\n按 Enter 继续...")
    
    try:
        from lerobot.robots.so_follower.so_follower import SOFollower
        from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
        
        print("\n[步骤1] 连接机械臂...")
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
        
        print("\n[步骤2] 清除故障锁存...")
        for motor_id, motor_name in motors.items():
            try:
                print(f"  正在清除电机 {motor_id} ({motor_name})...")
                
                # 地址48：Status_Error（清除保护标志）
                # 写入0清除所有故障标志
                try:
                    bus.write("Status_Error", 0, motor_name, normalize=False)
                    print(f"    ✓ 成功清除故障锁存")
                except Exception as e:
                    print(f"    ⚠️ 清除失败: {e}")
                    print(f"    可能原因：")
                    print(f"      1. 该舵机没有故障锁存")
                    print(f"      2. 该舵机硬件有问题")
                
            except Exception as e:
                print(f"    ✗ 操作失败: {e}")
        
        print("\n[步骤3] 验证舵机状态...")
        for motor_id, motor_name in motors.items():
            try:
                # 尝试读取状态
                pos = bus.read("Present_Position", motor_name, normalize=False)
                voltage = bus.read("Present_Voltage", motor_name, normalize=False)
                temp = bus.read("Present_Temperature", motor_name, normalize=False)
                
                print(f"  电机 {motor_id} ({motor_name}):")
                print(f"    位置: {pos}, 电压: {voltage/10:.1f}V, 温度: {temp}°C")
                
            except Exception as e:
                print(f"  电机 {motor_id} ({motor_name}): ❌ 无法读取 ({e})")
        
        master.disconnect()
        
        print("\n" + "="*70)
        print("清除完成！")
        print("="*70)
        
        print("\n下一步：")
        print("  1. 观察 LED 是否还闪烁")
        print("  2. 如果还闪烁，运行 python fix_voltage_limit.py 修复电压上限")
        print("  3. 如果正常，运行 python full_diagnosis.py 测试")
        
    except Exception as e:
        print(f"\n❌ 操作失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    clear_faults()