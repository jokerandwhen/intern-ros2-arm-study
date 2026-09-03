"""
只读诊断脚本：扫描 COM3/COM4 上的电机状态
不写入任何寄存器，安全无副作用
"""
import serial
import serial.tools.list_ports
import time
import sys

BAUDRATE = 1000000
MOTOR_IDS = list(range(1, 11))

# 寄存器地址（来自 lerobot SDK tables.py / 项目记忆）
REGISTERS = [
    ("Model_Number",        0, 2),
    ("Torque_Enable",      40, 1),   # 0=禁用 1=启用
    ("LED",                41, 1),
    ("Torque_Limit",       48, 2),   # 0-1023
    ("Present_Voltage",    62, 1),   # 实际电压×10
    ("Present_Temp",       63, 1),   # 实际温度℃
    ("Status/Error",       65, 1),   # 故障状态
]

def calc_checksum(data):
    return (~sum(data) & 0xFF)

def ping_motor(ser, motor_id):
    """Ping 电机，返回是否响应"""
    packet = bytes([0xFF, 0xFF, motor_id, 2, 0x01])
    checksum = calc_checksum(packet[2:])
    packet = packet + bytes([checksum])
    ser.reset_input_buffer()
    ser.write(packet)
    time.sleep(0.03)
    resp = ser.read(10)
    return len(resp) >= 4

def read_register(ser, motor_id, address, num_bytes):
    """读寄存器"""
    packet = bytes([0xFF, 0xFF, motor_id, 4, 0x02, address, num_bytes])
    checksum = calc_checksum(packet[2:])
    packet = packet + bytes([checksum])
    ser.reset_input_buffer()
    ser.write(packet)
    time.sleep(0.03)
    resp = ser.read(20)
    if len(resp) >= 8 + num_bytes:
        if num_bytes == 1:
            return resp[9]
        else:
            return resp[9] | (resp[10] << 8)
    return None

def diagnose_port(port_name):
    """诊断一个端口上的所有电机"""
    print(f"\n{'='*60}")
    print(f"扫描端口: {port_name}  (波特率 {BAUDRATE})")
    print('='*60)

    try:
        ser = serial.Serial(port_name, baudrate=BAUDRATE, timeout=0.1)
        time.sleep(0.3)
    except Exception as e:
        print(f"  ✗ 无法打开 {port_name}: {e}")
        return

    found = []
    for mid in MOTOR_IDS:
        if ping_motor(ser, mid):
            found.append(mid)
            print(f"\n  ✓ 发现电机 ID={mid}")

            for name, addr, nbytes in REGISTERS:
                val = read_register(ser, mid, addr, nbytes)
                if val is None:
                    print(f"      {name} (addr {addr}): 读取失败")
                else:
                    if name == "Present_Voltage":
                        print(f"      {name} (addr {addr}): {val/10:.1f}V  (raw={val})")
                    elif name == "Torque_Enable":
                        state = "启用(ON)" if val == 1 else "禁用(OFF)"
                        print(f"      {name} (addr {addr}): {state}  (raw={val})")
                    elif name == "Status/Error":
                        if val == 0:
                            print(f"      {name} (addr {addr}): 无故障 ✓  (raw={val})")
                        else:
                            faults = []
                            if val & 0x01: faults.append("过热")
                            if val & 0x02: faults.append("过压")
                            if val & 0x04: faults.append("欠压")
                            if val & 0x08: faults.append("过载/堵转")
                            if val & 0x10: faults.append("过流")
                            if val & 0x20: faults.append("过功率")
                            print(f"      {name} (addr {addr}): 故障! {', '.join(faults)} (raw={val:#04x})")
                    elif name == "Model_Number":
                        print(f"      {name} (addr {addr}): {val} (0x{val:04X})")
                    else:
                        print(f"      {name} (addr {addr}): {val}")
        else:
            # 只在扫描时显示，不逐个打印失败
            pass

    if not found:
        print(f"  ✗ 未发现任何电机（ID 1-10 均无响应）")
        print(f"    可能原因: 电源未接/波特率不对/舵机驱动板故障")
    else:
        print(f"\n  共发现 {len(found)} 个电机: {found}")

    ser.close()

def main():
    print("="*60)
    print("SoArm101 电机状态只读诊断")
    print("="*60)

    # 列出可用串口
    ports = list(serial.tools.list_ports.comports())
    print(f"\n检测到 {len(ports)} 个串口:")
    for p in ports:
        print(f"  - {p.device}: {p.description}")

    # 诊断 COM3 和 COM4
    for port in ["COM3", "COM4"]:
        diagnose_port(port)

    print(f"\n{'='*60}")
    print("诊断完成")
    print('='*60)
    print("\n诊断结果解读:")
    print("  - Torque_Enable=0 (OFF): 扭矩禁用，臂是软的能手动动但不响应指令")
    print("  - Torque_Enable=1 (ON):  扭矩启用，臂应该能响应指令")
    print("  - Status/Error≠0:  电机故障，需要清除故障并断电重启")
    print("  - Present_Voltage: 正常范围 5V-12V，过低会触发欠压故障")

if __name__ == "__main__":
    main()
