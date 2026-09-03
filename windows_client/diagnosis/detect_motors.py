"""
检测串口上的电机设备
用于确认COM3和COM4连接的设备类型
"""

import serial
import serial.tools.list_ports
import time

def detect_motors_on_port(port_name):
    """尝试检测指定串口上的设备"""
    print(f"\n{'='*50}")
    print(f"检测串口: {port_name}")
    print('='*50)

    try:
        # 尝试以不同波特率打开串口
        baudrates = [1000000, 500000, 115200, 9600]

        for baudrate in baudrates:
            try:
                print(f"\n尝试波特率: {baudrate}")
                ser = serial.Serial(port_name, baudrate, timeout=1)
                time.sleep(0.5)

                if ser.is_open:
                    print(f"✓ 串口已打开")

                    # 清空缓冲区
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()

                    # 尝试读取数据（如果有设备主动发送数据）
                    print("等待设备响应...")
                    time.sleep(1)

                    if ser.in_waiting > 0:
                        data = ser.read(ser.in_waiting)
                        print(f"收到数据: {data.hex()}")
                    else:
                        print("无主动响应")

                    ser.close()
                    print(f"✓ 串口已关闭")

            except Exception as e:
                print(f"✗ 波特率 {baudrate} 失败: {e}")

    except Exception as e:
        print(f"✗ 无法打开串口 {port_name}: {e}")

def main():
    """主函数"""
    print("串口电机设备检测工具")
    print("="*50)

    # 列出所有可用串口
    ports = serial.tools.list_ports.comports()
    print(f"\n检测到 {len(ports)} 个串口设备:")
    for port in ports:
        print(f"  - {port.device}: {port.description} ({port.hwid})")

    # 检测每个串口
    for port in ports:
        detect_motors_on_port(port.device)

    print("\n" + "="*50)
    print("检测完成")
    print("="*50)
    print("\n建议:")
    print("1. 如果COM3可以检测到电机，说明是SoArm101机械臂")
    print("2. 如果COM4检测不到电机，可能是其他设备或未通电")
    print("3. 检查机械臂是否已连接12V电源适配器")

if __name__ == "__main__":
    main()