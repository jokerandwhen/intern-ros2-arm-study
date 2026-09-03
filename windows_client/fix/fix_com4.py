"""
COM4主臂专项修复：修复电压限值、温度限值、清除故障
根因：
  地址10(Temp_Limit)=3°C → 任何温度都触发过热
  地址12(Max_Voltage_Limit)=0V → 任何电压都触发过压
  地址17(Alarm_Shutdown)=0x03 → 过压+过热时自动关机闪灯
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
    time.sleep(0.02)
    ser.read(20)

def safe(v, fmt="d"):
    if v is None: return "N/A"
    if fmt == "x": return f"0x{v:02X}"
    if fmt == "v": return f"{v/10:.1f}V"
    return str(v)

print("=" * 60)
print("COM4 主臂专项修复")
print("=" * 60)

ser = serial.Serial(PORT, baudrate=BAUD, timeout=0.2)
time.sleep(0.3)

# 先扫描实际电机ID（可能不是1-6）
print("\n--- 扫描实际电机ID ---")
motor_ids = []
for mid in range(1, 13):
    ser.reset_input_buffer()
    ser.write(build_packet(mid, 0x01))
    time.sleep(0.03)
    if len(ser.read(20)) >= 6:
        motor_ids.append(mid)
        print(f"  ID {mid}: ✓ 在线")

if not motor_ids:
    print("  没有找到电机！尝试ID 7-12...")
    for mid in range(7, 13):
        ser.reset_input_buffer()
        ser.write(build_packet(mid, 0x01))
        time.sleep(0.03)
        if len(ser.read(20)) >= 6:
            motor_ids.append(mid)
            print(f"  ID {mid}: ✓ 在线")

print(f"\n找到 {len(motor_ids)} 个电机: {motor_ids}")

# 对每个电机进行修复
for mid in motor_ids:
    print(f"\n{'='*50}")
    print(f"修复电机 ID={mid}")
    print(f"{'='*50}")
    
    # 读取当前状态
    fault = read1(ser, mid, 48)
    temp_limit = read1(ser, mid, 10)
    min_v = read1(ser, mid, 11)
    max_v = read1(ser, mid, 12)
    alarm_shutdown = read1(ser, mid, 17)
    voltage = read1(ser, mid, 62)
    temp = read1(ser, mid, 63)
    lock = read1(ser, mid, 55)
    
    print(f"修复前: 故障={safe(fault,'x')}  温度限值={temp_limit}°C  电压限值={min_v}-{max_v}  关机告警={safe(alarm_shutdown,'x')}")
    print(f"        当前电压={safe(voltage,'v')}  当前温度={temp}°C  锁={lock}")
    
    # Step 1: 清除故障
    write1(ser, mid, 48, 0)
    time.sleep(0.01)
    
    # Step 2: 解锁EEPROM
    write1(ser, mid, 55, 0)
    time.sleep(0.05)
    lock_check = read1(ser, mid, 55)
    print(f"  EEPROM解锁: {lock_check}")
    
    # Step 3: 修复温度限值 80°C
    print(f"  设置温度限值=80°C...")
    write1(ser, mid, 10, 80)
    time.sleep(0.01)
    
    # Step 4: 修复电压限值
    # 地址11=最低电压(0.1V单位), 设50=5.0V
    # 地址12=最高电压(0.1V单位), 设160=16.0V
    print(f"  设置电压限值: 最低=5.0V  最高=16.0V...")
    write1(ser, mid, 11, 60)
    time.sleep(0.01)
    write1(ser, mid, 12, 160)
    time.sleep(0.01)
    
    # Step 5: 修复关机告警条件
    # 地址17=0x04 (只在堵转时关机，不过压/过热关机)
    print(f"  设置关机告警=0x04 (仅堵转)...")
    write1(ser, mid, 17, 0x04)
    time.sleep(0.01)
    
    # Step 6: 确保角度限位正确
    # 地址11-12我们已经改了，但这里是Min_Angle = 0
    # 地址13-14: Max_Angle = 4095
    print(f"  确保角度限位正确...")
    write1(ser, mid, 13, 255)
    time.sleep(0.01)
    write1(ser, mid, 14, 15)
    time.sleep(0.01)
    
    # Step 7: 锁定EEPROM
    write1(ser, mid, 55, 1)
    time.sleep(0.05)
    
    # Step 8: 清除故障
    write1(ser, mid, 48, 0)
    time.sleep(0.02)
    write1(ser, mid, 48, 0)
    time.sleep(0.02)
    
    # 验证
    fault2 = read1(ser, mid, 48)
    temp_limit2 = read1(ser, mid, 10)
    min_v2 = read1(ser, mid, 11)
    max_v2 = read1(ser, mid, 12)
    alarm2 = read1(ser, mid, 17)
    voltage2 = read1(ser, mid, 62)
    
    print(f"修复后: 故障={safe(fault2,'x')}  温度限值={temp_limit2}°C  电压限值={min_v2/10:.1f}-{max_v2/10:.1f}V  关机告警={safe(alarm2,'x')}  当前电压={safe(voltage2,'v')}")
    
    ok = (fault2 == 0 and temp_limit2 == 80 and max_v2 == 160)
    print(f"  {'✓ 修复成功！' if ok else '⚠ 仍有问题'}")

# 最终验证
print(f"\n{'='*60}")
print("最终验证（等待1秒后）")
print(f"{'='*60}")
time.sleep(1)

for mid in motor_ids:
    fault = read1(ser, mid, 48)
    voltage = read1(ser, mid, 62)
    temp = read1(ser, mid, 63)
    temp_limit = read1(ser, mid, 10)
    max_v = read1(ser, mid, 12)
    alarm = read1(ser, mid, 17)
    
    ok = fault == 0
    print(f"  {'✓' if ok else '⚠'} ID{mid}: 故障={safe(fault,'x')}  电压={safe(voltage,'v')}  温度={temp}°C  温度限值={temp_limit}°C  电压上限={safe(max_v/10,'v') if max_v else 'N/A'}  关机告警={safe(alarm,'x')}")

ser.close()
print(f"\n{'='*60}")
print("请观察主臂LED是否停止闪烁")
print(f"{'='*60}")