"""
SoArm101 主从同步脚本（纯 pyserial 模式）- 修正寄存器版本

基于lerobot STS3215权威寄存器表 (tables.py)
关键寄存器（正确地址）:
  Torque_Enable = 40 (1字节, 0=禁用, 1=使能)
  Goal_Position = 42 (2字节, 目标位置)
  Present_Position = 56 (2字节, 当前位置)
  Status = 65 (1字节, 只读, 状态/错误)
  Lock = 55 (1字节, EEPROM锁)
  Torque_Limit = 48 (2字节, 运行时扭矩限制)

重要：绝不操作EEPROM（不写地址9-39），只操作SRAM（地址40+）
只做四件事：读取位置、写入目标位置、使能/禁用扭矩、设置加速度
"""

import time
import serial

MOTORS = {1: "shoulder_pan", 2: "shoulder_lift", 3: "elbow_flex", 4: "wrist_flex", 5: "wrist_roll", 6: "gripper"}
LEADER_PORT = "COM4"
FOLLOWER_PORT = "COM3"
BAUD = 1000000

INSTR_PING = 0x01
INSTR_READ = 0x02
INSTR_WRITE = 0x03
INSTR_SYNC_WRITE = 0x83

# 正确的寄存器地址（来自lerobot STS3215控制表）
REG_TORQUE_ENABLE = 40    # 1字节
REG_GOAL_POSITION = 42    # 2字节
REG_PRESENT_POSITION = 56 # 2字节
REG_STATUS = 65           # 1字节, 只读
REG_ACCELERATION = 41     # 1字节

def build_packet(motor_id, instruction, params=b''):
    length = len(params) + 2
    packet = bytes([0xFF, 0xFF, motor_id, length, instruction]) + params
    checksum = (~sum(packet[2:]) & 0xFF)
    return packet + bytes([checksum])

def write_reg(ser, motor_id, address, value, num_bytes=1):
    if num_bytes == 1:
        params = bytes([address, value & 0xFF])
    else:
        params = bytes([address, value & 0xFF, (value >> 8) & 0xFF])
    ser.reset_input_buffer()
    ser.write(build_packet(motor_id, INSTR_WRITE, params))
    time.sleep(0.005)

def read_reg(ser, motor_id, address, num_bytes=1, retries=3):
    packet = build_packet(motor_id, INSTR_READ, bytes([address, num_bytes]))
    for _ in range(retries):
        ser.reset_input_buffer()
        ser.write(packet)
        time.sleep(0.015)
        resp = ser.read(64)
        if len(resp) >= 5 + num_bytes:
            if num_bytes == 1:
                return resp[5]
            else:
                return resp[5] | (resp[6] << 8)
    return None

def read_position(ser, motor_id):
    return read_reg(ser, motor_id, REG_PRESENT_POSITION, 2)

def read_status(ser, motor_id):
    """读取状态寄存器(地址65)，0x00表示正常"""
    return read_reg(ser, motor_id, REG_STATUS, 1)

def disable_torque(ser, motor_id):
    write_reg(ser, motor_id, REG_TORQUE_ENABLE, 0, 1)

def enable_torque(ser, motor_id):
    write_reg(ser, motor_id, REG_TORQUE_ENABLE, 1, 1)

def set_acceleration(ser, motor_id, accel=254):
    write_reg(ser, motor_id, REG_ACCELERATION, accel, 1)

def sync_write_goals(ser, positions_dict):
    start_addr = REG_GOAL_POSITION
    data_len = 2
    params = bytes([start_addr, data_len])
    for mid, pos in positions_dict.items():
        params += bytes([mid, pos & 0xFF, (pos >> 8) & 0xFF])
    packet = build_packet(0xFE, INSTR_SYNC_WRITE, params)
    ser.reset_input_buffer()
    ser.write(packet)
    time.sleep(0.005)

def prepare_arm(ser, port_name):
    """准备机械臂：禁用扭矩、设置加速度、不碰任何EEPROM"""
    print(f"\n[{port_name}] 准备机械臂...")
    ok_count = 0
    for mid in range(1, 7):
        ser.reset_input_buffer()
        ser.write(build_packet(mid, INSTR_PING))
        time.sleep(0.02)
        resp = ser.read(20)
        if len(resp) < 6:
            print(f"  电机{mid}: 离线!")
            continue
        # 禁用扭矩（同时清除故障锁存）
        disable_torque(ser, mid)
        time.sleep(0.01)
        # 设置加速度
        set_acceleration(ser, mid, 254)
        time.sleep(0.01)
        # 读取状态和位置
        status = read_status(ser, mid)
        pos = read_position(ser, mid)
        s_str = f"0x{status:02X}" if status is not None else "N/A"
        print(f"  电机{mid}: 状态={s_str} 位置={pos}")
        ok_count += 1
    return ok_count

# ============================================================
# 主程序
# ============================================================
print("=" * 60)
print("SoArm101 主从同步（修正寄存器版本）")
print("=" * 60)
print()
print("寄存器说明:")
print("  Torque_Enable=40, Goal_Position=42, Present_Position=56")
print("  Status=65(只读), Acceleration=41")
print("  绝不操作EEPROM(地址9-39)")
print()

leader_ser = serial.Serial(LEADER_PORT, baudrate=BAUD, timeout=0.1)
follower_ser = serial.Serial(FOLLOWER_PORT, baudrate=BAUD, timeout=0.1)
time.sleep(0.5)

prepare_arm(leader_ser, LEADER_PORT)
prepare_arm(follower_ser, FOLLOWER_PORT)

print("\n" + "=" * 60)
print("准备阶段")
print("=" * 60)
print("请手动将两个机械臂放在相同的中性位置")
print("=" * 60)

input("\n按 Enter 继续...")

# 读取当前位置
leader_hold = {}
follower_hold = {}
for mid in range(1, 7):
    leader_hold[mid] = read_position(leader_ser, mid) or 2048
    follower_hold[mid] = read_position(follower_ser, mid) or 2048

print("\n当前位置：")
for mid in range(1, 7):
    print(f"  {MOTORS[mid]}: 主臂={leader_hold[mid]}  从动臂={follower_hold[mid]}")

# 启用从动臂扭矩
print("\n启用从动臂扭矩...")
# 先写入目标位置
for _ in range(3):
    sync_write_goals(follower_ser, follower_hold)
    time.sleep(0.02)

for mid in range(1, 7):
    enable_torque(follower_ser, mid)
    time.sleep(0.005)

time.sleep(0.1)
for _ in range(3):
    sync_write_goals(follower_ser, follower_hold)
    time.sleep(0.02)
print("✓ 从动臂扭矩已启用")

# 读取初始位置
leader_init = {}
follower_init = {}
for mid in range(1, 7):
    leader_init[mid] = read_position(leader_ser, mid) or 2048
    follower_init[mid] = read_position(follower_ser, mid) or 2048

print("\n==== 同步已启动 ====")
print("拖动主臂，从动臂跟随")
print("Ctrl+C 停止\n")

frame = 0
try:
    while True:
        # 读取主臂位置
        leader_now = {}
        for mid in range(1, 7):
            pos = read_position(leader_ser, mid)
            leader_now[mid] = pos if pos is not None else leader_init[mid]

        # 计算目标
        action = {}
        for mid in range(1, 7):
            delta = leader_now[mid] - leader_init[mid]
            target = follower_init[mid] + delta
            action[mid] = max(0, min(4095, int(target)))

        # 写入从动臂
        sync_write_goals(follower_ser, action)

        # 读取从动臂实际位置
        follower_now = {}
        for mid in range(1, 7):
            pos = read_position(follower_ser, mid)
            follower_now[mid] = pos if pos is not None else -1

        frame += 1
        if frame % 10 == 0:
            sp_l = leader_now.get(1, 0)
            sp_a = follower_now.get(1, 0)
            sl_l = leader_now.get(2, 0)
            sl_t = action.get(2, 0)
            sl_a = follower_now.get(2, 0)
            gr_l = leader_now.get(6, 0)
            gr_t = action.get(6, 0)
            gr_a = follower_now.get(6, 0)
            print(f"[f{frame}] pan: {sp_l:4d}→{sp_a:4d} | lift: {sl_l:4d}→{sl_t:4d}→{sl_a:4d} | grip: {gr_l:4d}→{gr_t:4d}→{gr_a:4d}")

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\n停止...")
finally:
    for mid in range(1, 7):
        disable_torque(follower_ser, mid)
        disable_torque(leader_ser, mid)
    leader_ser.close()
    follower_ser.close()
    print("串口已关闭")
