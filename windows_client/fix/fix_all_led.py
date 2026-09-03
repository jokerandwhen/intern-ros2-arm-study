"""
彻底修复LED闪烁（两个臂所有电机）

根因分析（根据项目记忆验证）：
  - 舵机型号: 2563 (0x0A03)
  - 地址11-12: Min_Angle_Limit (2字节)
  - 地址13-14: Max_Angle_Limit (2字节)
  - 地址14 是 Max_Angle_Limit 的高字节，不是电压上限！
  - 之前的 fix_led.py 误把地址14写成160，导致 Max_Angle_Limit = (160<<8)|255 = 41215
  - 同时把地址15写成50，可能破坏了其他寄存器

正确修复流程（来自项目记忆）：
  1. 清除故障锁存: 地址48写0
  2. 解锁EEPROM: 地址55写0
  3. 设置角度限位: 地址11=0, 地址12=0, 地址13=255, 地址14=15 → 限位=0~4095
  4. 锁定EEPROM: 地址55写1
  5. 再次清除故障: 地址48写0

关键：用1字节分别写每个地址，绝不用2字节写（避免覆盖相邻地址）
"""

import serial
import time
import sys

PORTS = ["COM3", "COM4"]
BAUD = 1000000

# 寄存器地址
REG_TORQUE_ENABLE = 40
REG_GOAL_POSITION = 42
REG_PRESENT_POSITION = 56
REG_STATUS_ERROR = 48
REG_LOCK = 55
REG_MIN_ANGLE_L = 11
REG_MIN_ANGLE_H = 12
REG_MAX_ANGLE_L = 13
REG_MAX_ANGLE_H = 14
REG_PRESENT_VOLTAGE = 62
REG_PRESENT_TEMP = 63

def build_packet(motor_id, instruction, params=b''):
    length = len(params) + 2
    packet = bytes([0xFF, 0xFF, motor_id, length, instruction]) + params
    checksum = (~sum(packet[2:]) & 0xFF)
    return packet + bytes([checksum])

def write1(ser, mid, addr, val, retries=5):
    """写1字节寄存器（带重试）"""
    for attempt in range(retries):
        ser.reset_input_buffer()
        ser.write(build_packet(mid, 0x03, bytes([addr, val & 0xFF])))
        time.sleep(0.01)
        # 读取响应
        resp = ser.read(20)
        if len(resp) >= 4:
            return True
        time.sleep(0.02)
    return False

def read1(ser, mid, addr, retries=5):
    """读1字节寄存器（带重试）"""
    for attempt in range(retries):
        ser.reset_input_buffer()
        ser.write(build_packet(mid, 0x02, bytes([addr, 1])))
        time.sleep(0.02)
        r = ser.read(64)
        if len(r) >= 6:
            return r[5]
        time.sleep(0.03)
    return None

def read2(ser, mid, addr, retries=5):
    """读2字节寄存器（带重试）"""
    for attempt in range(retries):
        ser.reset_input_buffer()
        ser.write(build_packet(mid, 0x02, bytes([addr, 2])))
        time.sleep(0.02)
        r = ser.read(64)
        if len(r) >= 7:
            return r[5] | (r[6] << 8)
        time.sleep(0.03)
    return None

def ping(ser, mid, retries=3):
    """Ping电机"""
    for attempt in range(retries):
        ser.reset_input_buffer()
        ser.write(build_packet(mid, 0x01))
        time.sleep(0.03)
        if len(ser.read(20)) >= 6:
            return True
        time.sleep(0.02)
    return False

def safe_str(val, fmt="d"):
    """安全格式化数值"""
    if val is None:
        return "N/A"
    if fmt == "02X":
        return f"0x{val:02X}"
    if fmt == "v":  # 电压格式
        return f"{val/10:.1f}V"
    return str(val)

def diagnose_motor(ser, mid):
    """诊断单个电机"""
    fault = read1(ser, mid, REG_STATUS_ERROR)
    min_angle = read2(ser, mid, REG_MIN_ANGLE_L)
    max_angle = read2(ser, mid, REG_MAX_ANGLE_L)
    a11 = read1(ser, mid, REG_MIN_ANGLE_L)
    a12 = read1(ser, mid, REG_MIN_ANGLE_H)
    a13 = read1(ser, mid, REG_MAX_ANGLE_L)
    a14 = read1(ser, mid, REG_MAX_ANGLE_H)
    a15 = read1(ser, mid, 15)
    a16 = read1(ser, mid, 16)
    voltage = read1(ser, mid, REG_PRESENT_VOLTAGE)
    temp = read1(ser, mid, REG_PRESENT_TEMP)
    pos = read2(ser, mid, REG_PRESENT_POSITION)
    lock = read1(ser, mid, REG_LOCK)
    
    print(f"  电机{mid}:")
    print(f"    故障={safe_str(fault, '02X')}  位置={safe_str(pos)}  电压={safe_str(voltage, 'v')}  温度={safe_str(temp)}°C  锁={safe_str(lock)}")
    print(f"    地址11={safe_str(a11)}  地址12={safe_str(a12)}  → Min_Angle={safe_str(min_angle)}")
    print(f"    地址13={safe_str(a13)}  地址14={safe_str(a14)}  → Max_Angle={safe_str(max_angle)}")
    print(f"    地址15={safe_str(a15)}  地址16={safe_str(a16)}")
    
    # 判断问题
    problems = []
    if fault is not None and fault != 0:
        problems.append(f"故障码=0x{fault:02X}")
    if max_angle is not None and max_angle != 4095:
        problems.append(f"Max_Angle={max_angle}(应为4095)")
    if min_angle is not None and min_angle != 0:
        problems.append(f"Min_Angle={min_angle}(应为0)")
    if a14 is not None and a14 != 15:
        problems.append(f"地址14={a14}(应为15, 之前被错误写成160)")
    
    if problems:
        print(f"    ⚠ 问题: {', '.join(problems)}")
    else:
        print(f"    ✓ 寄存器值正常")
    
    return {
        'fault': fault, 'min_angle': min_angle, 'max_angle': max_angle,
        'a14': a14, 'a15': a15, 'voltage': voltage, 'problems': problems
    }

def fix_motor(ser, mid):
    """修复单个电机"""
    print(f"\n  --- 修复电机{mid} ---")
    
    # Step 1: 先清除故障
    print(f"    [1] 清除故障...")
    write1(ser, mid, REG_STATUS_ERROR, 0)
    time.sleep(0.02)
    
    # Step 2: 解锁EEPROM
    print(f"    [2] 解锁EEPROM...")
    if not write1(ser, mid, REG_LOCK, 0):
        print(f"    ⚠ 解锁EEPROM失败，重试...")
        time.sleep(0.1)
        write1(ser, mid, REG_LOCK, 0)
    time.sleep(0.05)
    
    # 验证解锁
    lock_val = read1(ser, mid, REG_LOCK)
    print(f"    EEPROM锁状态: {safe_str(lock_val)}")
    
    # Step 3: 设置Min_Angle_Limit = 0 (地址11=0, 地址12=0)
    print(f"    [3] 设置Min_Angle=0...")
    write1(ser, mid, REG_MIN_ANGLE_L, 0)
    time.sleep(0.01)
    write1(ser, mid, REG_MIN_ANGLE_H, 0)
    time.sleep(0.01)
    
    # Step 4: 设置Max_Angle_Limit = 4095 (地址13=255, 地址14=15)
    # 4095 = 0x0FF → 低字节=0xFF=255, 高字节=0x0F=15
    print(f"    [4] 设置Max_Angle=4095 (地址13=255, 地址14=15)...")
    write1(ser, mid, REG_MAX_ANGLE_L, 255)
    time.sleep(0.01)
    write1(ser, mid, REG_MAX_ANGLE_H, 15)
    time.sleep(0.01)
    
    # Step 5: 锁定EEPROM
    print(f"    [5] 锁定EEPROM...")
    write1(ser, mid, REG_LOCK, 1)
    time.sleep(0.05)
    
    # Step 6: 再次清除故障
    print(f"    [6] 清除故障...")
    write1(ser, mid, REG_STATUS_ERROR, 0)
    time.sleep(0.01)
    
    # Step 7: 禁用扭矩
    print(f"    [7] 禁用扭矩...")
    write1(ser, mid, REG_TORQUE_ENABLE, 0)
    time.sleep(0.01)
    
    # Step 8: 最后清除故障
    write1(ser, mid, REG_STATUS_ERROR, 0)
    time.sleep(0.02)
    
    # 验证
    fault_new = read1(ser, mid, REG_STATUS_ERROR)
    max_angle_new = read2(ser, mid, REG_MAX_ANGLE_L)
    min_angle_new = read2(ser, mid, REG_MIN_ANGLE_L)
    a14_new = read1(ser, mid, REG_MAX_ANGLE_H)
    
    print(f"    验证: 故障={safe_str(fault_new, '02X')}  Min_Angle={safe_str(min_angle_new)}  Max_Angle={safe_str(max_angle_new)}  地址14={safe_str(a14_new)}")
    
    ok = True
    if fault_new is not None and fault_new != 0:
        print(f"    ⚠ 故障未清零")
        ok = False
    if max_angle_new is not None and max_angle_new != 4095:
        print(f"    ⚠ Max_Angle不正确")
        ok = False
    if a14_new is not None and a14_new != 15:
        print(f"    ⚠ 地址14不正确")
        ok = False
    
    if ok:
        print(f"    ✓ 修复成功！")
    return ok

def fix_port(port):
    print(f"\n{'='*60}")
    print(f"处理端口: {port}")
    print(f"{'='*60}")
    
    try:
        ser = serial.Serial(port, baudrate=BAUD, timeout=0.3)
    except Exception as e:
        print(f"  ❌ 无法打开 {port}: {e}")
        return False
    
    time.sleep(0.5)
    
    # 阶段1：诊断
    print(f"\n--- 阶段1：诊断 ---")
    motor_status = {}
    for mid in range(1, 7):
        if not ping(ser, mid):
            print(f"  电机{mid}: 离线！")
            motor_status[mid] = None
            continue
        motor_status[mid] = diagnose_motor(ser, mid)
    
    # 阶段2：修复
    print(f"\n--- 阶段2：修复 ---")
    fixed_count = 0
    for mid in range(1, 7):
        if motor_status[mid] is None:
            continue
        # 无论是否有问题都执行修复（确保一致）
        if fix_motor(ser, mid):
            fixed_count += 1
    
    # 阶段3：最终验证
    print(f"\n--- 阶段3：最终验证 ---")
    time.sleep(1)
    all_ok = True
    for mid in range(1, 7):
        if motor_status[mid] is None:
            print(f"  电机{mid}: 离线")
            all_ok = False
            continue
        fault = read1(ser, mid, REG_STATUS_ERROR)
        max_angle = read2(ser, mid, REG_MAX_ANGLE_L)
        voltage = read1(ser, mid, REG_PRESENT_VOLTAGE)
        ok = (fault is not None and fault == 0 and 
              max_angle is not None and max_angle == 4095)
        symbol = "✓" if ok else "⚠"
        print(f"  {symbol} 电机{mid}: 故障={safe_str(fault, '02X')}  Max_Angle={safe_str(max_angle)}  电压={safe_str(voltage, 'v')}")
        if not ok:
            all_ok = False
    
    ser.close()
    
    print(f"\n  {port} 结果: {fixed_count}/6 电机已修复, {'全部正常' if all_ok else '仍有问题'}")
    return all_ok

# ============================================================
# 主程序
# ============================================================
print("=" * 60)
print("彻底修复LED闪烁 - 两个臂所有电机")
print("=" * 60)
print()
print("修复内容:")
print("  1. 清除故障锁存 (地址48=0)")
print("  2. 解锁EEPROM (地址55=0)")
print("  3. 恢复角度限位 (地址11-12=0, 地址13-14=4095)")
print("     地址13=255, 地址14=15 (4095=0x0FF)")
print("  4. 锁定EEPROM (地址55=1)")
print("  5. 清除故障 + 禁用扭矩")
print()
print("重要：地址14是Max_Angle高字节(=15)，不是电压上限！")
print("      之前fix_led.py把地址14写成160是错误的！")
print()

# 确认
input("确保两个臂都已通电，按 Enter 开始修复...")

results = {}
for port in PORTS:
    results[port] = fix_port(port)

# 总结
print(f"\n{'='*60}")
print("修复总结")
print(f"{'='*60}")
all_success = True
for port in PORTS:
    status = "✓ 全部正常" if results[port] else "⚠ 仍有问题"
    print(f"  {port}: {status}")
    if not results[port]:
        all_success = False

if all_success:
    print(f"\n✓ 所有电机修复完成！")
    print("  请观察LED是否已停止闪烁")
    print("  如果还有个别电机闪灯，可能需要断电重新上电")
else:
    print(f"\n⚠ 部分电机仍有问题")
    print("  请尝试：")
    print("    1. 断开电源，等待10秒")
    print("    2. 重新连接电源")
    print("    3. 再次运行此脚本")
    print("    4. 如果仍失败，检查电机连接线是否松动")

print(f"\n{'='*60}")
