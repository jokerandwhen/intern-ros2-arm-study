"""
彻底修复两个臂所有电机 - 正确寄存器布局
型号: 2563 (0x0A03)
地址10: Temperature_Limit (温度限值)
地址11: Min_Voltage_Limit (最低电压)
地址12: Max_Voltage_Limit (最高电压)
地址13-14: Max_Torque_Limit (最大扭矩)
地址16: Alarm_LED (告警LED行为)
地址17: Alarm_Shutdown (关机条件)
地址48: Status_Error (故障锁存)
地址55: EEPROM_Lock (EEPROM锁)

修复后必须断电重启让EEPROM生效！
"""
import serial
import time

PORTS = ["COM3", "COM4"]
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

def write1(ser, mid, addr, val):
    ser.reset_input_buffer()
    ser.write(build_packet(mid, 0x03, bytes([addr, val & 0xFF])))
    time.sleep(0.02)
    ser.read(20)
    time.sleep(0.01)

def ping(ser, mid):
    for _ in range(3):
        ser.reset_input_buffer()
        ser.write(build_packet(mid, 0x01))
        time.sleep(0.03)
        if len(ser.read(20)) >= 6:
            return True
        time.sleep(0.02)
    return False

def safe(v, fmt="d"):
    if v is None: return "N/A"
    if fmt == "x": return f"0x{v:02X}"
    if fmt == "v": return f"{v/10:.1f}V"
    return str(v)

def fix_port(port):
    print(f"\n{'='*55}")
    print(f"修复 {port}")
    print(f"{'='*55}")
    
    try:
        ser = serial.Serial(port, baudrate=BAUD, timeout=0.3)
    except Exception as e:
        print(f"  无法打开 {port}: {e}")
        return False
    
    time.sleep(0.5)
    all_ok = True
    
    for mid in range(1, 7):
        if not ping(ser, mid):
            print(f"\n  电机{mid}: 离线！")
            all_ok = False
            continue
        
        # 诊断
        fault = read1(ser, mid, 48)
        voltage = read1(ser, mid, 62)
        temp = read1(ser, mid, 63)
        a10 = read1(ser, mid, 10)
        a11 = read1(ser, mid, 11)
        a12 = read1(ser, mid, 12)
        a13 = read1(ser, mid, 13)
        a14 = read1(ser, mid, 14)
        a16 = read1(ser, mid, 16)
        a17 = read1(ser, mid, 17)
        lock = read1(ser, mid, 55)
        
        print(f"\n  电机{mid}: 故障={safe(fault,'x')} 电压={safe(voltage,'v')} 温度={safe(temp)}C")
        vmin = f"{a11/10:.1f}" if a11 is not None else "?"
        vmax = f"{a12/10:.1f}" if a12 is not None else "?"
        print(f"    修复前: 温限={safe(a10)}C 电压限=[{vmin}-{vmax}]V 扭矩限={safe(a13)}|{safe(a14)} LED={safe(a16)} 关机={safe(a17,'x')} 锁={safe(lock)}")
        
        # 判断需要修复什么
        needs_fix = (a10 is not None and a10 < 70) or \
                   (a12 is not None and a12 < 100) or \
                   (a17 is not None and a17 != 4)
        
        if not needs_fix and fault == 0:
            print(f"    ✓ 无需修复")
            continue
        
        # === 修复流程 ===
        # 1. 清除故障
        write1(ser, mid, 48, 0)
        time.sleep(0.02)
        
        # 2. 解锁EEPROM
        write1(ser, mid, 55, 0)
        time.sleep(0.05)
        l = read1(ser, mid, 55)
        print(f"    解锁EEPROM: {l}")
        
        # 3. 写温度限值 = 80°C
        write1(ser, mid, 10, 80)
        time.sleep(0.02)
        
        # 4. 写电压限值: 最低=5.0V, 最高=16.0V
        write1(ser, mid, 11, 60)
        time.sleep(0.02)
        write1(ser, mid, 12, 160)
        time.sleep(0.02)
        
        # 5. 写最大扭矩限值 = 1023 (0x03FF)
        write1(ser, mid, 13, 255)
        time.sleep(0.02)
        write1(ser, mid, 14, 3)
        time.sleep(0.02)
        
        # 6. 写告警LED = 0 (不闪烁)
        write1(ser, mid, 16, 0)
        time.sleep(0.02)
        
        # 7. 写关机条件 = 0x04 (仅堵转时关机)
        write1(ser, mid, 17, 4)
        time.sleep(0.02)
        
        # 8. 锁定EEPROM
        write1(ser, mid, 55, 1)
        time.sleep(0.05)
        
        # 9. 反复清除故障
        for _ in range(5):
            write1(ser, mid, 48, 0)
            time.sleep(0.02)
        
        # 10. 禁用扭矩
        write1(ser, mid, 40, 0)
        time.sleep(0.02)
        
        # 验证
        fault2 = read1(ser, mid, 48)
        a10_2 = read1(ser, mid, 10)
        a12_2 = read1(ser, mid, 12)
        a17_2 = read1(ser, mid, 17)
        a16_2 = read1(ser, mid, 16)
        
        vmax2 = f"{a12_2/10:.1f}" if a12_2 is not None else "?"
        print(f"    修复后: 故障={safe(fault2,'x')} 温限={safe(a10_2)}C 压上限={vmax2}V LED={safe(a16_2)} 关机={safe(a17_2,'x')}")
        
        if a10_2 == 80 and a12_2 == 160 and a17_2 == 4 and a16_2 == 0:
            print(f"    ✓ EEPROM写入成功")
        else:
            print(f"    ⚠ EEPROM写入可能失败")
            all_ok = False
    
    ser.close()
    return all_ok

# ============================================================
print("=" * 55)
print("彻底修复两个臂 - 型号2563寄存器布局")
print("=" * 55)
print()
print("修复内容:")
print("  地址10: 温度限值 → 80°C")
print("  地址11: 最低电压 → 6.0V")
print("  地址12: 最高电压 → 16.0V")
print("  地址13-14: 最大扭矩 → 1023")
print("  地址16: 告警LED → 0 (不闪烁)")
print("  地址17: 关机条件 → 0x04 (仅堵转)")
print("  地址48: 清除故障锁存")
print()
print("⚠ 重要: 修复后请断电10秒再重新上电！")
print("  EEPROM修改需要断电重启才能被电机加载")
print()

input("确保两个臂都已通电，按 Enter 开始...")

results = {}
for port in PORTS:
    results[port] = fix_port(port)

print(f"\n{'='*55}")
print("修复总结")
print(f"{'='*55}")
for port in PORTS:
    status = "✓" if results[port] else "⚠"
    print(f"  {status} {port}")

print()
print("=" * 55)
print("⚠ 关键步骤：请立即执行以下操作：")
print("=" * 55)
print("  1. 断开两个臂的电源")
print("  2. 等待10秒")
print("  3. 重新连接电源")
print("  4. 告诉我'已重启'，我帮你清除故障")
print("=" * 55)