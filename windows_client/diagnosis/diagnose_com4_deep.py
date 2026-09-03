"""
深度诊断COM4主臂：扫描所有寄存器，找出LED闪烁根因
"""
import serial
import time

PORT = "COM4"
BAUD = 1000000

def build_packet(motor_id, instruction, params=b''):
    length = len(params) + 2
    packet = bytes([0xFF, 0xFF, motor_id, length, instruction]) + params
    checksum = (~sum(packet[2:]) & 0xFF)
    return packet + bytes([checksum])

def read1(ser, mid, addr):
    ser.reset_input_buffer()
    ser.write(build_packet(mid, 0x02, bytes([addr, 1])))
    time.sleep(0.02)
    r = ser.read(64)
    return r[5] if len(r) >= 6 else None

def read2(ser, mid, addr):
    ser.reset_input_buffer()
    ser.write(build_packet(mid, 0x02, bytes([addr, 2])))
    time.sleep(0.02)
    r = ser.read(64)
    return r[5] | (r[6] << 8) if len(r) >= 7 else None

def write1(ser, mid, addr, val):
    ser.reset_input_buffer()
    ser.write(build_packet(mid, 0x03, bytes([addr, val & 0xFF])))
    time.sleep(0.015)
    resp = ser.read(20)

def ping(ser, mid):
    ser.reset_input_buffer()
    ser.write(build_packet(mid, 0x01))
    time.sleep(0.03)
    return len(ser.read(20)) >= 6

print("=" * 60)
print("COM4 主臂深度诊断")
print("=" * 60)

ser = serial.Serial(PORT, baudrate=BAUD, timeout=0.2)
time.sleep(0.3)

# 选择电机1作为代表，扫描所有寄存器
print("\n--- 扫描电机1全部寄存器 (0-70) ---")
print(f"{'地址':>5}  {'值':>5}  {'说明'}")
print("-" * 40)

# 已知的关键寄存器
key_regs = {
    0: "Model_L",
    1: "Model_H",
    2: "Firmware",
    3: "ID",
    4: "Baud",
    5: "Return_Delay",
    6: "CW_Angle_Limit_L",
    7: "CW_Angle_Limit_H",
    8: "CCW_Angle_Limit_L",
    9: "CCW_Angle_Limit_H",
    10: "Temp_Limit",
    11: "Min_Voltage_Limit",
    12: "Max_Voltage_Limit",
    13: "Max_Torque_Limit_L",
    14: "Max_Torque_Limit_H",
    15: "Status_Return",
    16: "Alarm_LED",
    17: "Alarm_Shutdown",
    18: "Multi_Turn_Offset_L",
    19: "Multi_Turn_Offset_H",
    20: "Resolution_Divider",
    21: "P_Coef",
    22: "I_Coef",
    23: "D_Coef",
    24: "Min_Position_L",
    25: "Min_Position_H",
    26: "Max_Position_L",
    27: "Max_Position_H",
    28: "Torque_Enable",
    29: "LED",
    30: "Goal_Position_L",
    31: "Goal_Position_H",
    32: "Goal_Speed_L",
    33: "Goal_Speed_H",
    34: "Goal_Torque_L",
    35: "Goal_Torque_H",
    40: "Torque_Enable(2)",
    42: "Goal_Position_L(2)",
    43: "Goal_Position_H(2)",
    44: "Goal_Speed_L(2)",
    45: "Goal_Speed_H(2)",
    48: "Status_Error",
    50: "Present_Voltage",
    51: "Present_Temperature",
    52: "Present_Load_L",
    53: "Present_Load_H",
    54: "Present_Speed_L",
    55: "Present_Speed_H",
    56: "Present_Position_L",
    57: "Present_Position_H",
    62: "Current_Voltage",
    63: "Current_Temperature",
}

for addr in range(0, 71):
    val = read1(ser, 1, addr)
    desc = key_regs.get(addr, "")
    if val is not None:
        print(f"  {addr:3d}  0x{val:02X}  {val:3d}  {desc}")
    else:
        print(f"  {addr:3d}  N/A     {desc}")

print("\n--- 逐个电机诊断 ---")
for mid in range(1, 7):
    if not ping(ser, mid):
        print(f"\n电机{mid}: 离线！")
        continue
    
    fault = read1(ser, mid, 48)
    voltage = read1(ser, mid, 62)
    temp = read1(ser, mid, 63)
    load = read2(ser, mid, 52)
    pos = read2(ser, mid, 56)
    speed = read2(ser, mid, 54)
    
    # 读取地址11-16（之前被修复的区域）
    a11 = read1(ser, mid, 11)
    a12 = read1(ser, mid, 12)
    a13 = read1(ser, mid, 13)
    a14 = read1(ser, mid, 14)
    a15 = read1(ser, mid, 15)
    a16 = read1(ser, mid, 16)
    lock = read1(ser, mid, 55)
    
    # 故障码分析
    fault_str = ""
    if fault is not None and fault != 0:
        if fault & 0x01: fault_str += "过热 "
        if fault & 0x02: fault_str += "过压 "
        if fault & 0x04: fault_str += "堵转/过载 "
        if fault & 0x08: fault_str += "角度超限 "
        if fault & 0x10: fault_str += "过流 "
    
    print(f"\n电机{mid}:")
    print(f"  故障=0x{fault:02X} ({fault_str})" if fault else f"  故障=0x00")
    print(f"  电压={voltage/10:.1f}V  温度={temp}°C  负载={load}  速度={speed}")
    print(f"  位置={pos}  锁={lock}")
    print(f"  地址11={a11}  地址12={a12}  地址13={a13}  地址14={a14}  地址15={a15}  地址16={a16}")

# 快速测试：清除故障后观察是否立即复现
print("\n\n--- 故障复现测试 ---")
print("清除电机5故障，观察5秒内是否复现...")
for i in range(5):
    write1(ser, 5, 48, 0)
    time.sleep(0.1)
    fault = read1(ser, 5, 48)
    if fault is not None and fault != 0:
        print(f"  t={i*0.1:.1f}s: 故障=0x{fault:02X} ← 立即复现！")
    else:
        print(f"  t={i*0.1:.1f}s: 故障=0x00")

ser.close()
print("\n诊断完成")