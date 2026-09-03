"""
读取电机2和6的电压上限寄存器
诊断闪烁原因
"""

import serial
import time

print("=" * 60)
print("电机电压上限诊断")
print("=" * 60)

# 打开COM3
print("\n打开 COM3...")
try:
    ser = serial.Serial("COM3", baudrate=1000000, timeout=1)
    time.sleep(1)
except Exception as e:
    print(f"❌ 无法打开COM3: {e}")
    exit(1)

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

print("\n读取电机状态...")

for motor_id in [2, 6]:
    print(f"\n=== 电机 {motor_id} ===")
    
    # 读取电压相关寄存器
    voltage_limit = read_register(motor_id, 14, 1)  # Max_Voltage_Limit (地址14)
    min_voltage = read_register(motor_id, 12, 1)    # Min_Voltage_Limit (地址12)
    present_voltage = read_register(motor_id, 62, 1) # Present_Voltage (地址62)
    
    print(f"  Max_Voltage_Limit (地址14): {voltage_limit} ({voltage_limit/10:.1f}V)")
    print(f"  Min_Voltage_Limit (地址12): {min_voltage} ({min_voltage/10:.1f}V)")
    print(f"  Present_Voltage (地址62): {present_voltage} ({present_voltage/10:.1f}V)")
    
    # 读取限位和扭矩
    min_angle = read_register(motor_id, 11, 2)
    max_angle = read_register(motor_id, 13, 2)
    max_torque = read_register(motor_id, 15, 2)
    
    print(f"  Min_Angle_Limit (地址11): {min_angle}")
    print(f"  Max_Angle_Limit (地址13): {max_angle}")
    print(f"  Max_Torque_Limit (地址15): {max_torque}")
    
    # 读取工作模式
    work_mode = read_register(motor_id, 10, 1)
    print(f"  Work_Mode (地址10): {work_mode}")
    
    # 诊断
    if voltage_limit and voltage_limit < 100:
        print(f"\n  ⚠️ 电压上限设置过低！")
        print(f"  当前: {voltage_limit/10:.1f}V")
        print(f"  建议: 16.0V (数值160)")
        print(f"  需要修改电压上限寄存器")
    
    if min_angle == 0 and max_angle == 4095:
        print(f"  ✓ 限位已解除 [0, 4095]")
    else:
        print(f"  ⚠️ 限位未解除: [{min_angle}, {max_angle}]")

ser.close()
print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)