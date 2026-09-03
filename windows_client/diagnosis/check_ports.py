"""
自动检测并清理串口占用
"""

import serial.tools.list_ports
import subprocess
import time

def check_and_clean_ports():
    """检测并清理串口占用"""
    
    print("="*70)
    print("串口检测和清理工具")
    print("="*70)
    
    # 检测串口
    print("\n[步骤1] 检测可用串口...")
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        print("✗ 未检测到任何串口设备")
        return False
    
    print(f"✓ 检测到 {len(ports)} 个串口：")
    for port in ports:
        print(f"  - {port.device}: {port.description}")
    
    # 尝试打开COM3和COM4
    print("\n[步骤2] 测试串口访问...")
    
    for port_name in ["COM3", "COM4"]:
        try:
            # 尝试打开串口
            ser = serial.Serial(port_name, baudrate=115200, timeout=1)
            print(f"✓ {port_name} 可以访问")
            ser.close()
        except serial.SerialException as e:
            print(f"✗ {port_name} 访问失败: {e}")
            print(f"  可能原因：")
            print(f"    1. 端口被其他程序占用")
            print(f"    2. 需要管理员权限")
            
            # 尝试关闭占用进程
            print(f"\n  尝试关闭占用进程...")
            try:
                subprocess.run(["powershell", "-Command", 
                    f"Get-WmiObject Win32_SerialPort | Where-Object {{$_.DeviceID -eq '{port_name}'}} | Select-Object -Property ProcessId"],
                    capture_output=True, text=True)
                
                # 强制关闭Python进程
                subprocess.run(["powershell", "-Command", 
                    "Get-Process python* | Stop-Process -Force"],
                    capture_output=True, text=True)
                
                print(f"  已尝试清理Python进程")
                time.sleep(2)
                
                # 再次测试
                try:
                    ser = serial.Serial(port_name, baudrate=115200, timeout=1)
                    print(f"✓ {port_name} 现在可以访问了")
                    ser.close()
                except:
                    print(f"✗ {port_name} 仍然无法访问")
                    print(f"  请手动关闭占用该端口的程序，或重启电脑")
            
            except Exception as e:
                print(f"  清理失败: {e}")
    
    print("\n" + "="*70)
    print("建议：")
    print("  1. 关闭所有Python程序后重试")
    print("  2. 以管理员身份运行PowerShell")
    print("  3. 如果仍然失败，重启电脑")
    print("="*70)
    
    return True

if __name__ == "__main__":
    check_and_clean_ports()