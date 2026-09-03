"""
COM3从动臂 欠压修复
问题：USB供电只有4.9V，低于Min_Voltage_Limit=5.0V → 欠压闪灯
修复：把Min_Voltage_Limit从50(5.0V)降到45(4.5V)
"""
import serial, time

PORT = "COM3"
BAUD = 1000000

def bpkt(mid, instr, params=b''):
    length = len(params) + 2
    pkt = bytes([0xFF,0xFF,mid,length,instr]) + params
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

print("=" * 50)
print("COM3 欠压修复 - 降低Min_Voltage到4.5V")
print("=" * 50)

ser = serial.Serial(PORT, baudrate=BAUD, timeout=0.3)
time.sleep(0.5)

all_ok = True
for mid in range(1, 7):
    if not ping(ser, mid):
        print(f"\n电机{mid}: 离线！")
        all_ok = False
        continue
    
    v = read1(ser, mid, 62)
    min_v = read1(ser, mid, 15)
    status = read1(ser, mid, 65)
    
    print(f"\n电机{mid}: 当前V={v/10:.1f}V MinV={min_v/10:.1f}V Status=0x{status:02X}")
    
    # 解锁EEPROM
    write1(ser, mid, 55, 0)
    time.sleep(0.05)
    
    # 写Min_Voltage_Limit = 45 (4.5V)
    write1(ser, mid, 15, 45)
    time.sleep(0.02)
    
    # 锁定EEPROM
    write1(ser, mid, 55, 1)
    time.sleep(0.05)
    
    # 禁用扭矩（清除故障锁存）
    write1(ser, mid, 40, 0)
    time.sleep(0.02)
    
    # 验证
    min_v2 = read1(ser, mid, 15)
    status2 = read1(ser, mid, 65)
    v2 = read1(ser, mid, 62)
    print(f"  修复后: V={v2/10:.1f}V MinV={min_v2/10:.1f}V Status=0x{status2:02X}")
    
    if min_v2 == 45:
        print(f"  ✓ 欠压阈值已设为4.5V")
    else:
        print(f"  ⚠ 写入可能失败")
        all_ok = False

ser.close()

print(f"\n{'='*50}")
if all_ok:
    print("✓ COM3修复完成！")
    print("  Min_Voltage_Limit = 4.5V")
    print("  USB 4.9V供电不再触发欠压保护")
else:
    print("⚠ 部分电机可能需要重试")
print(f"{'='*50}")
print()
print("请观察LED是否停止闪烁")