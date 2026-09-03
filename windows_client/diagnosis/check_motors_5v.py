"""
5V USB供电修复脚本
如果电机在12V下无法检测，尝试用5V USB供电
"""

import serial
import time

print("=" * 60)
print("电机5V修复脚本")
print("=" * 60)
print("\n请按以下步骤操作：")
print("1. 断开从动臂的12V电源")
print("2. 只用USB线连接舵机驱动板到电脑")
print("3. 确认COM端口是COM3")
print("4. 按 Enter 继续...")
input()

# 打开COM3
print("\n打开 COM3...")
try:
    ser = serial.Serial("COM3", baudrate=1000000, timeout=1)
    time.sleep(1)
except Exception as e:
    print(f"❌ 无法打开COM3: {e}")
    exit(1)

def ping_motor(motor_id):
    """Ping电机"""
    packet = bytes([0xFF, 0xFF, motor_id, 2, 0x01])
    checksum = (~sum(packet[2:]) & 0xFF)
    packet = packet + bytes([checksum])
    
    ser.write(packet)
    time.sleep(0.05)
    
    response = ser.read(10)
    return len(response) > 0

print("\n扫描所有电机（1-6）...")
for motor_id in range(1, 7):
    if ping_motor(motor_id):
        print(f"✓ 电机{motor_id}: 在线")
    else:
        print(f"❌ 电机{motor_id}: 离线")

print("\n如果电机2和6离线，请检查：")
print("  1. 电机连接线是否松动")
print("  2. 舵机驱动板跳线是否短接")
print("  3. 尝试重新插拔USB线")

ser.close()
print("\n完成")