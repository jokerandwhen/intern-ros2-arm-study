"""
根治LED闪烁：修复电压上限寄存器

根因分析：
  地址13 = Max_Angle_Limit 低字节 (1字节)
  地址14 = Max_Voltage_Limit 电压上限 (1字节, 单位0.1V)
  之前用2字节写地址13(=4095=0x0FF)，高字节0x0F=15被写入地址14
  导致电压上限变成1.5V，所有电机触发过压保护闪红灯

修复方案：
  1. 用1字节写地址13=255 (Max_Angle低字节，不影响地址14)
  2. 用1字节写地址14=160 (电压上限=16.0V)
  3. 清除故障
  绝不用2字节写入地址11或13！
"""

import serial
import time

PORTS = ["COM3", "COM4"]
BAUD = 1000000

def build_packet(motor_id, instruction, params=b''):
    length = len(params) + 2
    packet = bytes([0xFF, 0xFF, motor_id, length, instruction]) + params
    checksum = (~sum(packet[2:]) & 0xFF)
    return packet + bytes([checksum])

def write1(ser, mid, addr, val):
    """写1字节寄存器"""
    ser.reset_input_buffer()
    ser.write(build_packet(mid, 0x03, bytes([addr, val & 0xFF])))
    time.sleep(0.005)

def read1(ser, mid, addr):
    """读1字节寄存器"""
    ser.reset_input_buffer()
    ser.write(build_packet(mid, 0x02, bytes([addr, 1])))
    time.sleep(0.015)
    r = ser.read(64)
    return r[5] if len(r) >= 6 else None

def read2(ser, mid, addr):
    """读2字节寄存器"""
    ser.reset_input_buffer()
    ser.write(build_packet(mid, 0x02, bytes([addr, 2])))
    time.sleep(0.015)
    r = ser.read(64)
    return r[5] | (r[6] << 8) if len(r) >= 7 else None

def ping(ser, mid):
    ser.reset_input_buffer()
    ser.write(build_packet(mid, 0x01))
    time.sleep(0.02)
    return len(ser.read(20)) >= 6

def fix_port(port):
    print(f"\n{'='*50}")
    print(f"修复 {port}")
    print(f"{'='*50}")

    try:
        ser = serial.Serial(port, baudrate=BAUD, timeout=0.2)
    except Exception as e:
        print(f"  无法打开 {port}: {e}")
        return

    time.sleep(0.3)

    for mid in range(1, 7):
        if not ping(ser, mid):
            print(f"  电机{mid}: 离线")
            continue

        # 读取修复前的状态
        fault_old = read1(ser, mid, 48)
        addr13_old = read1(ser, mid, 13)
        addr14_old = read1(ser, mid, 14)
        addr15_old = read1(ser, mid, 15)
        present_v = read1(ser, mid, 62)
        temp = read1(ser, mid, 63)
        pos = read2(ser, mid, 56)

        print(f"\n  电机{mid}:")
        print(f"    修复前: 故障=0x{fault_old:02X}  地址13={addr13_old}  地址14(电压上限)={addr14_old}({addr14_old/10:.1f}V)  地址15(电压下限)={addr15_old}({addr15_old/10:.1f}V)")
        print(f"    当前: 电压={present_v/10:.1f}V  温度={temp}°C  位置={pos}")

        # Step 1: 清除故障
        write1(ser, mid, 48, 0)
        time.sleep(0.01)

        # Step 2: 解锁EEPROM
        write1(ser, mid, 55, 0)
        time.sleep(0.01)

        # Step 3: 用1字节写地址13 = 255 (Max_Angle低字节，不碰地址14)
        write1(ser, mid, 13, 255)
        time.sleep(0.01)

        # Step 4: 用1字节写地址14 = 160 (电压上限=16.0V)
        write1(ser, mid, 14, 160)
        time.sleep(0.01)

        # Step 5: 用1字节写地址15 = 50 (电压下限=5.0V)
        write1(ser, mid, 15, 50)
        time.sleep(0.01)

        # Step 6: 用1字节写地址11 = 0 (Min_Angle低字节，不碰地址12)
        write1(ser, mid, 11, 0)
        time.sleep(0.01)

        # Step 7: 用1字节写地址12 = 0 (Min_Angle高字节 或 其他)
        write1(ser, mid, 12, 0)
        time.sleep(0.01)

        # Step 8: 锁定EEPROM
        write1(ser, mid, 55, 1)
        time.sleep(0.01)

        # Step 9: 再次清除故障
        write1(ser, mid, 48, 0)
        time.sleep(0.01)

        # 禁用扭矩
        write1(ser, mid, 40, 0)
        time.sleep(0.01)

        # 再次清除故障
        write1(ser, mid, 48, 0)
        time.sleep(0.02)

        # 验证
        fault_new = read1(ser, mid, 48)
        addr13_new = read1(ser, mid, 13)
        addr14_new = read1(ser, mid, 14)
        addr15_new = read1(ser, mid, 15)

        print(f"    修复后: 故障=0x{fault_new:02X}  地址13={addr13_new}  地址14(电压上限)={addr14_new}({addr14_new/10:.1f}V)  地址15(电压下限)={addr15_new}({addr15_new/10:.1f}V)")

        if fault_new == 0 and addr14_new == 160:
            print(f"    ✓ 修复成功！")
        elif addr14_new == 160:
            print(f"    ⚠ 电压上限已修复，但故障未清零（可能需要断电重启）")
        else:
            print(f"    ✗ 修复失败")

    ser.close()

# ============================================================
print("=" * 50)
print("根治LED闪烁：修复电压上限寄存器")
print("=" * 50)
print()
print("根因：用2字节写地址13(Max_Angle)时，")
print("      高字节覆盖了地址14(电压上限)，变成1.5V")
print("      导致所有电机过压保护闪红灯")
print()
print("修复：用1字节分别写地址13和地址14")
print("      绝不用2字节写地址11或13")

for port in PORTS:
    fix_port(port)

# 最终验证
print(f"\n{'='*50}")
print("最终验证（等待2秒后读取）")
print(f"{'='*50}")
time.sleep(2)

for port in PORTS:
    print(f"\n[{port}]")
    try:
        ser = serial.Serial(port, baudrate=BAUD, timeout=0.2)
        time.sleep(0.2)
        for mid in range(1, 7):
            if not ping(ser, mid):
                print(f"  电机{mid}: 离线")
                continue
            fault = read1(ser, mid, 48)
            v14 = read1(ser, mid, 14)
            v15 = read1(ser, mid, 15)
            pv = read1(ser, mid, 62)
            fs = f"0x{fault:02X}" if fault is not None else "N/A"
            v14s = f"{v14/10:.1f}V" if v14 is not None else "N/A"
            v15s = f"{v15/10:.1f}V" if v15 is not None else "N/A"
            pvs = f"{pv/10:.1f}V" if pv is not None else "N/A"
            ok = "✓" if fault == 0 else "⚠"
            print(f"  {ok} 电机{mid}: 故障={fs}  上限={v14s}  下限={v15s}  当前={pvs}")
        ser.close()
    except Exception as e:
        print(f"  端口错误: {e}")

print(f"\n{'='*50}")
print("请观察LED是否停止闪烁")
print(f"{'='*50}")
