"""
COM4 正确寄存器诊断和修复
基于 lerobot STS3215 权威寄存器表 (tables.py)
"""
import serial, time

PORT = "COM4"
BAUD = 1000000

# STS3215 权威寄存器映射 (地址, 字节长度)
REGS = [
    (0, 1, "Firmware_Major"),
    (1, 1, "Firmware_Minor"),
    (3, 2, "Model_Number"),
    (5, 1, "ID"),
    (6, 1, "Baud_Rate"),
    (7, 1, "Return_Delay"),
    (8, 1, "Response_Level"),
    (9, 2, "Min_Position_Limit"),
    (11, 2, "Max_Position_Limit"),
    (13, 1, "Max_Temp_Limit"),
    (14, 1, "Max_Voltage_Limit"),
    (15, 1, "Min_Voltage_Limit"),
    (16, 2, "Max_Torque_Limit"),
    (18, 1, "Phase"),
    (19, 1, "Unloading_Cond"),
    (20, 1, "LED_Alarm_Cond"),
    (21, 1, "P_Coef"),
    (22, 1, "D_Coef"),
    (23, 1, "I_Coef"),
    (24, 2, "Min_Startup_Force"),
    (26, 1, "CW_Dead_Zone"),
    (27, 1, "CCW_Dead_Zone"),
    (28, 2, "Protection_Current"),
    (30, 1, "Angular_Resolution"),
    (31, 2, "Homing_Offset"),
    (33, 1, "Operating_Mode"),
    (34, 1, "Protective_Torque"),
    (35, 1, "Protection_Time"),
    (36, 1, "Overload_Torque"),
    (37, 1, "Vel_P_Gain"),
    (38, 1, "Overcurr_Prot_Time"),
    (39, 1, "Vel_I_Gain"),
    (40, 1, "Torque_Enable"),
    (41, 1, "Acceleration"),
    (42, 2, "Goal_Position"),
    (44, 2, "Goal_Time"),
    (46, 2, "Goal_Velocity"),
    (48, 2, "Torque_Limit"),
    (55, 1, "Lock"),
    (56, 2, "Present_Position"),
    (58, 2, "Present_Velocity"),
    (60, 2, "Present_Load"),
    (62, 1, "Present_Voltage"),
    (63, 1, "Present_Temp"),
    (65, 1, "Status"),
    (66, 1, "Moving"),
    (80, 1, "Moving_Vel_Thresh"),
    (84, 1, "Max_Velocity_Limit"),
    (85, 1, "Max_Acceleration"),
]

def bpkt(mid, instr, params=b''):
    length = len(params) + 2
    pkt = bytes([0xFF, 0xFF, mid, length, instr]) + params
    cs = (~sum(pkt[2:]) & 0xFF)
    return pkt + bytes([cs])

def read1(ser, mid, addr):
    for _ in range(3):
        ser.reset_input_buffer()
        ser.write(bpkt(mid, 0x02, bytes([addr, 1])))
        time.sleep(0.015)
        r = ser.read(64)
        if len(r) >= 6: return r[5]
        time.sleep(0.02)
    return None

def read2(ser, mid, addr):
    for _ in range(3):
        ser.reset_input_buffer()
        ser.write(bpkt(mid, 0x02, bytes([addr, 2])))
        time.sleep(0.015)
        r = ser.read(64)
        if len(r) >= 7: return r[5] | (r[6] << 8)
        time.sleep(0.02)
    return None

def write1(ser, mid, addr, val):
    for _ in range(3):
        ser.reset_input_buffer()
        ser.write(bpkt(mid, 0x03, bytes([addr, val & 0xFF])))
        time.sleep(0.015)
        resp = ser.read(20)
        if len(resp) >= 4: return True
        time.sleep(0.02)
    return False

def ping(ser, mid):
    for _ in range(3):
        ser.reset_input_buffer()
        ser.write(bpkt(mid, 0x01))
        time.sleep(0.02)
        if len(ser.read(20)) >= 6: return True
        time.sleep(0.02)
    return False

print("=" * 70)
print("STS3215 权威寄存器诊断 - COM4")
print("=" * 70)

ser = serial.Serial(PORT, baudrate=BAUD, timeout=0.2)
time.sleep(0.3)

# 先读电机1的所有寄存器
mid = 1
if not ping(ser, mid):
    print("电机1不在线，尝试其他电机...")
    for test_id in range(1, 7):
        if ping(ser, test_id):
            mid = test_id
            break
    else:
        print("没有电机在线！")
        ser.close()
        exit(1)

print(f"\n--- 电机{mid} 全部寄存器 ---")
print(f"{'地址':>4} {'长度':>4} {'名称':<25} {'当前值':>10} {'期望值':>10} {'状态'}")
print("-" * 75)

for addr, size, name in REGS:
    if size == 1:
        val = read1(ser, mid, addr)
    else:
        val = read2(ser, mid, addr)
    print(f"  {addr:2d}   {size}   {name:<25} {str(val):>10}")

ser.close()