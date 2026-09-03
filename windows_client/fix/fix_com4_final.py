"""
COM4主臂最终修复：恢复角度限位 + 恢复被破坏的寄存器

确认的寄存器布局（项目记忆验证）：
  地址11-12: Min_Angle_Limit (2字节) → 应为0
  地址13-14: Max_Angle_Limit (2字节) → 应为4095 (addr13=255, addr14=15)
  地址48: 故障状态
  地址55: EEPROM锁

fix_both_arms.py 误写了以下寄存器，需要恢复：
  addr10: 80→3 (恢复原值)
  addr11: 60→0 (Min_Angle_L)
  addr12: 160→0 (Min_Angle_H)
  addr13: 255 (正确)
  addr14: 3→15 (Max_Angle_H, 4095=0x0FF)
  addr16: 0→3 (恢复原值)
  addr17: 4→3 (恢复原值)
"""
import serial
import time

PORT = "COM4"
BAUD = 1000000

def build_packet(mid, instr, params=b''):
    length = len(params) + 2
    pkt = bytes([0xFF, 0xFF, mid, length, instr]) + params
    cs = (~sum(pkt[2:]) & 0xFF)
    return pkt + bytes([cs])

def read1(ser, mid, addr):
    for _ in range(3):
        ser.reset_input_buffer()
        ser.write(build_packet(mid, 0x02, bytes([addr, 1])))
        time.sleep(0.02)
        r = ser.read(64)
        if len(r) >= 6:
            return r[5]
        time.sleep(0.03)
    return None

def read2(ser, mid, addr):
    for _ in range(3):
        ser.reset_input_buffer()
        ser.write(build_packet(mid, 0x02, bytes([addr, 2])))
        time.sleep(0.02)
        r = ser.read(64)
        if len(r) >= 7:
            return r[5] | (r[6] << 8)
        time.sleep(0.03)
    return None

def write1(ser, mid, addr, val):
    for _ in range(3):
        ser.reset_input_buffer()
        ser.write(build_packet(mid, 0x03, bytes([addr, val & 0xFF])))
        time.sleep(0.02)
        resp = ser.read(20)
        if len(resp) >= 4:
            return True
        time.sleep(0.03)
    return False

def ping(ser, mid):
    for _ in range(3):
        ser.reset_input_buffer()
        ser.write(build_packet(mid, 0x01))
        time.sleep(0.03)
        if len(ser.read(20)) >= 6:
            return True
        time.sleep(0.02)
    return False

print("=" * 55)
print("COM4 主臂最终修复 - 恢复角度限位")
print("=" * 55)

ser = serial.Serial(PORT, baudrate=BAUD, timeout=0.3)
time.sleep(0.5)

all_ok = True
for mid in range(1, 7):
    if not ping(ser, mid):
        print(f"\n电机{mid}: 离线！")
        all_ok = False
        continue
    
    # 读取当前状态
    min_angle = read2(ser, mid, 11)
    max_angle = read2(ser, mid, 13)
    fault = read1(ser, mid, 48)
    
    print(f"\n电机{mid}: 故障=0x{fault:02X}  Min_Angle={min_angle}  Max_Angle={max_angle}")
    
    if min_angle == 0 and max_angle == 4095 and fault == 0:
        print(f"  ✓ 已正确，跳过")
        continue
    
    # === 修复 ===
    # 1. 清除故障
    write1(ser, mid, 48, 0)
    time.sleep(0.02)
    
    # 2. 解锁EEPROM
    write1(ser, mid, 55, 0)
    time.sleep(0.05)
    
    # 3. 恢复 addr10 = 3 (原值)
    write1(ser, mid, 10, 3)
    time.sleep(0.02)
    
    # 4. 恢复 Min_Angle = 0 (addr11=0, addr12=0)
    write1(ser, mid, 11, 0)
    time.sleep(0.02)
    write1(ser, mid, 12, 0)
    time.sleep(0.02)
    
    # 5. 恢复 Max_Angle = 4095 (addr13=255, addr14=15)
    write1(ser, mid, 13, 255)
    time.sleep(0.02)
    write1(ser, mid, 14, 15)
    time.sleep(0.02)
    
    # 6. 恢复 addr16 = 3 (原值)
    write1(ser, mid, 16, 3)
    time.sleep(0.02)
    
    # 7. 恢复 addr17 = 3 (原值)
    write1(ser, mid, 17, 3)
    time.sleep(0.02)
    
    # 8. 锁定EEPROM
    write1(ser, mid, 55, 1)
    time.sleep(0.05)
    
    # 9. 反复清除故障
    for _ in range(5):
        write1(ser, mid, 48, 0)
        time.sleep(0.02)
    
    # 验证
    min_angle2 = read2(ser, mid, 11)
    max_angle2 = read2(ser, mid, 13)
    fault2 = read1(ser, mid, 48)
    a10 = read1(ser, mid, 10)
    a14 = read1(ser, mid, 14)
    a16 = read1(ser, mid, 16)
    a17 = read1(ser, mid, 17)
    
    print(f"  修复后: 故障=0x{fault2:02X}  Min_Angle={min_angle2}  Max_Angle={max_angle2}")
    print(f"          a10={a10} a14={a14} a16={a16} a17={a17}")
    
    if min_angle2 == 0 and max_angle2 == 4095:
        print(f"  ✓ 角度限位已恢复正确")
    else:
        print(f"  ⚠ 角度限位仍不正确")
        all_ok = False

ser.close()

print(f"\n{'='*55}")
if all_ok:
    print("✓ COM4 所有电机修复完成！")
else:
    print("⚠ 部分电机仍有问题")
print(f"{'='*55}")
print()
print("现在请观察主臂LED是否停止闪烁")
print("如果还在闪，请断电10秒后重新上电")