"""
清除电机故障锁存并尝试恢复通信
"""

import serial
import time

print("=" * 60)
print("电机故障清除脚本")
print("=" * 60)

print("\n请确认：")
print("1. 从动臂已连接12V电源")
print("2. USB线已连接")
print("3. 舵机驱动板跳线已短接")
print("\n按 Enter 继续...")
input()

# 打开COM3
print("\n打开 COM3...")
try:
    ser = serial.Serial("COM3", baudrate=1000000, timeout=1)
    time.sleep(1)
except Exception as e:
    print(f"❌ 无法打开COM3: {e}")
    exit(1)

def write_register(motor_id, address, value, num_bytes=2):
    """写寄存器"""
    if num_bytes == 1:
        packet = bytes([0xFF, 0xFF, motor_id, 4, 0x03, address, value])
    else:
        low = value & 0xFF
        high = (value >> 8) & 0xFF
        packet = bytes([0xFF, 0xFF, motor_id, 5, 0x03, address, low, high])
    
    checksum = (~sum(packet[2:]) & 0xFF)
    packet = packet + bytes([checksum])
    
    ser.write(packet)
    time.sleep(0.05)

def read_register(motor_id, address, num_bytes=2):
    """读寄存器"""
    packet = bytes([0xFF, 0xFF, motor_id, 4, 0x02, address, num_bytes])
    checksum = (~sum(packet[2:]) & 0xFF)
    packet = packet + bytes([checksum])
    
    ser.write(packet)
    time.sleep(0.05)
    
    response = ser.read(20)
    if len(response) >= 8 + num_bytes:
        if num_bytes == 1:
            return response[9]
        else:
            return response[9] | (response[10] << 8)
    return None

print("\n尝试清除故障锁存...")

for motor_id in [2, 6]:
    print(f"\n=== 电机 {motor_id} ===")
    
    # 清除故障锁存（地址48写0）
    print("清除故障锁存（地址48）...")
    write_register(motor_id, 48, 0, 1)
    time.sleep(0.1)
    
    # 尝试读取故障状态
    fault = read_register(motor_id, 48, 1)
    if fault is not None:
        print(f"  故障状态: {fault}")
    else:
        print(f"  无法读取故障状态")
    
    # 解锁EEPROM
    print("解锁EEPROM...")
    write_register(motor_id, 55, 0, 1)
    time.sleep(0.05)
    
    # 修改电压上限为16.0V（数值160）
    print("修改电压上限为16.0V...")
    write_register(motor_id, 14, 160, 1)
    time.sleep(0.05)
    
    # 修改电压下限为5.0V（数值50）
    print("修改电压下限为5.0V...")
    write_register(motor_id, 12, 50, 1)
    time.sleep(0.05)
    
    # 解除角度限位
    print("解除角度限位 [0, 4095]...")
    write_register(motor_id, 11, 0)
    time.sleep(0.05)
    write_register(motor_id, 13, 4095)
    time.sleep(0.05)
    
    # 设置最大扭矩
    print("设置最大扭矩1023...")
    write_register(motor_id, 15, 1023)
    time.sleep(0.05)
    
    # 锁定EEPROM
    print("锁定EEPROM...")
    write_register(motor_id, 55, 1, 1)
    time.sleep(0.1)
    
    # 验证
    print("\n验证修改...")
    voltage_limit = read_register(motor_id, 14, 1)
    min_voltage = read_register(motor_id, 12, 1)
    min_angle = read_register(motor_id, 11, 2)
    max_angle = read_register(motor_id, 13, 2)
    
    if voltage_limit is not None:
        print(f"  电压上限: {voltage_limit/10:.1f}V")
    if min_voltage is not None:
        print(f"  电压下限: {min_voltage/10:.1f}V")
    if min_angle is not None and max_angle is not None:
        print(f"  角度限位: [{min_angle}, {max_angle}]")

ser.close()
print("\n" + "=" * 60)
print("故障清除完成")
print("=" * 60)
print("\n请断开12V电源，等待10秒，再重新连接")
print("然后运行 python diagnose_voltage.py 验证")