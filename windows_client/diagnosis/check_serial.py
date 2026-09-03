import serial.tools.list_ports
import serial

# 列出所有串口
ports = serial.tools.list_ports.comports()
print("可用串口：")
for port in ports:
    print(f"  - {port.device}: {port.description}")
    
    # 尝试打开串口
    try:
        ser = serial.Serial(port.device, 115200, timeout=1)
        print(f"    ✓ 可以打开 {port.device}")
        ser.close()
    except Exception as e:
        print(f"    ✗ 打开失败: {e}")

# 特别检查COM3
print("\n检查COM3：")
try:
    ser = serial.Serial('COM3', 115200, timeout=1)
    print("✓ COM3可以打开，波特率115200")
    ser.write(b'\n')  # 发送测试
    ser.close()
except Exception as e:
    print(f"✗ COM3打开失败: {e}")