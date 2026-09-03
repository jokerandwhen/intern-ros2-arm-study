"""
COM3从动臂 正确修复脚本 - 使用lerobot权威STS3215寄存器表
与fix_com4_correct.py使用相同的正确寄存器映射
"""
import serial, time

PORT = "COM3"
BAUD = 1000000

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
    for _ in range(5):
        ser.reset_input_buffer()
        ser.write(bpkt(mid, 0x03, bytes([addr, val & 0xFF])))
        time.sleep(0.02)
        resp = ser.read(20)
        if len(resp) >= 4: return True
        time.sleep(0.02)
    return False

def ping(ser, mid):
    for _ in range(3):
        ser.reset_input_buffer()
        ser.write(bpkt(mid, 0x01))
        time.sleep(0.03)
        if len(ser.read(20)) >= 6: return True
        time.sleep(0.02)
    return False

print("=" * 60)
print("COM3 从动臂正确修复 (STS3215 权威寄存器表)")
print("=" * 60)

ser = serial.Serial(PORT, baudrate=BAUD, timeout=0.3)
time.sleep(0.5)

all_ok = True
for mid in range(1, 7):
    if not ping(ser, mid):
        print(f"\n电机{mid}: 离线！")
        all_ok = False
        continue
    
    # 读取当前状态
    min_pos = read2(ser, mid, 9)
    max_pos = read2(ser, mid, 11)
    max_temp = read1(ser, mid, 13)
    max_v = read1(ser, mid, 14)
    min_v = read1(ser, mid, 15)
    max_torque = read2(ser, mid, 16)
    phase = read1(ser, mid, 18)
    led_alarm = read1(ser, mid, 20)
    p_coef = read1(ser, mid, 21)
    op_mode = read1(ser, mid, 33)
    torque_en = read1(ser, mid, 40)
    torque_limit = read2(ser, mid, 48)
    lock = read1(ser, mid, 55)
    voltage = read1(ser, mid, 62)
    temp = read1(ser, mid, 63)
    status = read1(ser, mid, 65)
    
    print(f"\n电机{mid}: V={voltage/10:.1f}V T={temp}°C Status=0x{status:02X}")
    print(f"  修复前: MinPos={min_pos} MaxPos={max_pos} MaxTemp={max_temp}°C")
    print(f"          MaxV={max_v/10:.1f}V MinV={min_v/10:.1f}V MaxTorque={max_torque}")
    print(f"          Phase={phase} LEDAlarm=0x{led_alarm:02X} P={p_coef}")
    print(f"          TorqueEn={torque_en} TorqueLimit={torque_limit} Lock={lock}")
    
    # === 修复流程 ===
    # 1. 先禁用扭矩
    write1(ser, mid, 40, 0)
    time.sleep(0.02)
    
    # 2. 解锁EEPROM
    write1(ser, mid, 55, 0)
    time.sleep(0.05)
    
    # 3. 恢复 EEPROM 寄存器
    write1(ser, mid, 9, 0)
    time.sleep(0.02)
    write1(ser, mid, 10, 0)
    time.sleep(0.02)
    
    write1(ser, mid, 11, 255)
    time.sleep(0.02)
    write1(ser, mid, 12, 15)
    time.sleep(0.02)
    
    write1(ser, mid, 13, 80)
    time.sleep(0.02)
    
    write1(ser, mid, 14, 160)
    time.sleep(0.02)
    
    write1(ser, mid, 15, 50)
    time.sleep(0.02)
    
    write1(ser, mid, 16, 255)
    time.sleep(0.02)
    write1(ser, mid, 17, 3)
    time.sleep(0.02)
    
    if phase is not None:
        write1(ser, mid, 18, phase & ~0x10)
        time.sleep(0.02)
    
    write1(ser, mid, 20, 0x23)
    time.sleep(0.02)
    
    write1(ser, mid, 21, 16)
    time.sleep(0.02)
    
    write1(ser, mid, 22, 32)
    time.sleep(0.02)
    
    write1(ser, mid, 33, 0)
    time.sleep(0.02)
    
    # 4. 锁定EEPROM
    write1(ser, mid, 55, 1)
    time.sleep(0.05)
    
    # 5. 设置SRAM参数
    write1(ser, mid, 41, 254)
    time.sleep(0.02)
    
    write1(ser, mid, 48, 255)
    time.sleep(0.02)
    write1(ser, mid, 49, 3)
    time.sleep(0.02)
    
    write1(ser, mid, 85, 254)
    time.sleep(0.02)
    
    # 6. 禁用扭矩
    write1(ser, mid, 40, 0)
    time.sleep(0.02)
    
    # 验证
    min_pos2 = read2(ser, mid, 9)
    max_pos2 = read2(ser, mid, 11)
    max_temp2 = read1(ser, mid, 13)
    max_v2 = read1(ser, mid, 14)
    min_v2 = read1(ser, mid, 15)
    max_torque2 = read2(ser, mid, 16)
    torque_limit2 = read2(ser, mid, 48)
    status2 = read1(ser, mid, 65)
    led2 = read1(ser, mid, 20)
    
    print(f"  修复后: MinPos={min_pos2} MaxPos={max_pos2} MaxTemp={max_temp2}°C")
    print(f"          MaxV={max_v2/10:.1f}V MinV={min_v2/10:.1f}V MaxTorque={max_torque2}")
    print(f"          TorqueLimit={torque_limit2} LEDAlarm=0x{led2:02X} Status=0x{status2:02X}")
    
    ok = (min_pos2 == 0 and max_pos2 == 4095 and max_v2 == 160 and 
          max_temp2 == 80 and max_torque2 == 1023)
    print(f"  {'✓ 修复成功！' if ok else '⚠ 仍有问题'}")
    if not ok: all_ok = False

ser.close()

print(f"\n{'='*60}")
if all_ok:
    print("✓ COM3所有电机修复完成！")
else:
    print("⚠ 部分电机可能需要重新运行")
print(f"{'='*60}")
print()
print("请观察两个臂的LED是否停止闪烁。")
print("如果还在闪，请断电10秒后重新上电。")