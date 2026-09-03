"""
SoArm101 全面诊断脚本
自动检测所有硬件和软件问题
"""

import time
import sys

def check_hardware():
    """硬件检查清单"""
    print("="*70)
    print("硬件检查清单")
    print("="*70)
    
    checks = [
        ("主臂 USB 线是否已插入电脑？", "USB线"),
        ("主臂电源适配器（12V）是否已连接？", "电源适配器"),
        ("主臂电源开关是否已打开？", "电源开关"),
        ("主臂基座是否有指示灯亮起？", "基座指示灯"),
        ("所有关节是否能手动顺畅转动？", "关节转动"),
        ("所有电机连接线是否插紧？", "电机连接线"),
        ("是否有任何电机LED在闪烁？", "LED状态"),
    ]
    
    results = []
    for i, (question, name) in enumerate(checks, 1):
        print(f"\n[{i}/{len(checks)}] {question}")
        answer = input("  回答 (y/n): ").strip().lower()
        results.append((name, answer == 'y'))
    
    print("\n" + "="*70)
    print("检查结果")
    print("="*70)
    
    problems = []
    for name, status in results:
        symbol = "✓" if status else "✗"
        print(f"{symbol} {name}: {'正常' if status else '异常'}")
        if not status:
            problems.append(name)
    
    if problems:
        print(f"\n⚠️ 发现问题: {', '.join(problems)}")
        print("\n请先解决以上硬件问题，然后重新运行诊断。")
        return False
    else:
        print("\n✓ 所有硬件检查通过！")
        return True

def check_ports():
    """检查可用端口"""
    print("\n" + "="*70)
    print("端口检测")
    print("="*70)
    
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        
        if not ports:
            print("❌ 没有找到任何串口设备！")
            print("\n可能的原因：")
            print("  1. USB 线没有插入")
            print("  2. USB 驱动未安装")
            print("  3. 设备管理器中禁用了串口")
            return None
        
        print(f"\n找到 {len(ports)} 个串口设备：")
        for port in ports:
            print(f"  - {port.device}: {port.description}")
        
        # 尝试识别 SoArm101
        soarm_ports = []
        for port in ports:
            if 'USB' in port.description or 'Serial' in port.description:
                soarm_ports.append(port.device)
        
        if soarm_ports:
            print(f"\n✓ 可能的 SoArm101 端口: {', '.join(soarm_ports)}")
        
        return soarm_ports
        
    except Exception as e:
        print(f"❌ 端口检测失败: {e}")
        return None

def diagnose_motors(ports):
    """诊断电机状态"""
    print("\n" + "="*70)
    print("电机诊断")
    print("="*70)
    
    if not ports:
        print("❌ 没有可用端口，无法进行电机诊断")
        return
    
    from lerobot.robots.so_follower.so_follower import SOFollower
    from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
    
    for port in ports:
        print(f"\n尝试连接端口: {port}")
        
        master = None
        try:
            master_config = SOFollowerRobotConfig(port=port)
            master = SOFollower(master_config)
            master.connect(calibrate=False)
            
            print("✓ 连接成功！")
            
            # 读取所有电机状态
            bus = master.bus
            print("\n电机状态：")
            
            motor_names = ["shoulder_pan", "shoulder_lift", "elbow_flex", 
                          "wrist_flex", "wrist_roll", "gripper"]
            
            for name in motor_names:
                try:
                    pos = bus.read("Present_Position", name, normalize=False)
                    voltage = bus.read("Present_Voltage", name, normalize=False)
                    temp = bus.read("Present_Temperature", name, normalize=False)
                    
                    status = "正常"
                    if voltage < 60:  # 低于 6V
                        status = "⚠️ 电压过低"
                    elif temp > 70:  # 高于 70°C
                        status = "⚠️ 温度过高"
                    
                    print(f"  {name}: 位置={pos}, 电压={voltage/10:.1f}V, 温度={temp}°C {status}")
                    
                except Exception as e:
                    print(f"  {name}: ❌ 读取失败 ({e})")
            
            master.disconnect()
            break  # 成功连接一个端口就够了
            
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            if master:
                try:
                    master.disconnect()
                except:
                    pass

def main():
    """主函数"""
    print("\n" + "="*70)
    print("SoArm101 全面诊断")
    print("="*70)
    
    print("\n这个脚本会自动检查所有可能的问题。")
    print("请按照提示操作。\n")
    
    # 1. 硬件检查
    if not check_hardware():
        return
    
    # 2. 端口检测
    ports = check_ports()
    
    # 3. 电机诊断
    if ports:
        diagnose_motors(ports)
    
    print("\n" + "="*70)
    print("诊断完成")
    print("="*70)
    
    print("\n下一步：")
    print("  1. 如果所有检查都通过，运行 smart_mapping.py 测试同步")
    print("  2. 如果有问题，根据以上诊断结果解决")
    print("  3. 如果电机有问题，可能需要联系厂商技术支持")

if __name__ == "__main__":
    main()