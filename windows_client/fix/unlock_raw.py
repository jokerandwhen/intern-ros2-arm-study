"""
直接用底层SCServo协议解锁电机限位
"""

import serial
import time

# 打开COM3
print("打开 COM3...")
ser = serial.Serial("COM3", baudrate=1000000, timeout=1)
time.sleep(1)

def write_register(motor_id, address, value, num_bytes=2):
    """直接写寄存器"""
    if num_bytes == 1:
        # 写1字节
        packet = bytes([0xFF, 0xFF, motor_id, 4, 0x03, address, value])
    else:
        # 写2字节（低字节在前）
        low = value & 0xFF
        high = (value >> 8) & 0xFF
        packet = bytes([0xFF, 0xFF, motor_id, 5, 0x03, address, low, high])
    
    # 计算校验和
    checksum = (~sum(packet[2:]) & 0xFF)
    packet = packet + bytes([checksum])
    
    ser.write(packet)
    time.sleep(0.02)

def read_register(motor_id, address, num_bytes=2):
    """读寄存器"""
    packet = bytes([0xFF, 0xFF, motor_id, 4, 0x02, address, num_bytes])
    checksum = (~sum(packet[2:]) & 0xFF)
    packet = packet + bytes([checksum])
    
    ser.write(packet)
    time.sleep(0.02)
    
    # 读取响应
    response = ser.read(20)
    if len(response) >= 8 + num_bytes:
        if num_bytes == 1:
            return response[9]
        else:
            return response[9] | (response[10] << 8)
    return None

print("\n解锁电机2(shoulder_lift)和电机6(gripper)...")

for motor_id in [2, 6]:
    print(f"\n=== 电机 {motor_id} ===")
    
    # 读取当前限位
    min_limit = read_register(motor_id, 11, 2)
    max_limit = read_register(motor_id, 13, 2)
    max_torque = read_register(motor_id, 15, 2)
    print(f"当前限位: [{min_limit}, {max_limit}]  最大扭矩: {max_torque}")
    
    # 解锁EEPROM（地址55写0）
    print("解锁EEPROM...")
    write_register(motor_id, 55, 0, 1)
    time.sleep(0.1)
    
    # 写入新限位
    print("写入限位 [0, 4095]...")
    write_register(motor_id, 11, 0)
    time.sleep(0.05)
    write_register(motor_id, 13, 4095)
    time.sleep(0.05)
    write_register(motor_id, 15, 1023)
    time.sleep(0.05)
    
    # 锁定EEPROM（地址55写1）
    print("锁定EEPROM...")
    write_register(motor_id, 55, 1, 1)
    time.sleep(0.1)
    
    # 验证
    min_limit_new = read_register(motor_id, 11, 2)
    max_limit_new = read_register(motor_id, 13, 2)
    max_torque_new = read_register(motor_id, 15, 2)
    print(f"新限位: [{min_limit_new}, {max_limit_new}]  最大扭矩: {max_torque_new}")
    
    if min_limit_new == 0 and max_limit_new == 4095:
        print("✓ 解锁成功")
    else:
        print("⚠️ 解锁可能失败")

ser.close()
print("\n✓ 完成！请重新运行 sync.py")