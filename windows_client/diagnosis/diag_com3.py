"""
只读诊断：只检测 COM3 从动臂
"""
import serial
import time

BAUDRATE = 1000000
MOTOR_IDS = list(range(1, 21))  # 扫描 ID 1-20

REGISTERS = [
    ("Model_Number",       0, 2),
    ("Torque_Enable",     40, 1),
    ("Torque_Limit",      48, 2),
    ("Present_Voltage",    62, 1),
    ("Present_Temp",       63, 1),
    ("Status/Error",       65, 1),
]

def calc_checksum(data):
    return (~sum(data) & 0xFF)

def ping_motor(ser, motor_id, timeout=0.05):
    packet = bytes([0xFF, 0xFF, motor_id, 2, 0x01])
    checksum = calc_checksum(packet[2:])
    packet = packet + bytes([checksum])
    ser.reset_input_buffer()
    ser.write(packet)
    time.sleep(timeout)
    resp = ser.read(20)
    return resp

def read_register(ser, motor_id, address, num_bytes):
    packet = bytes([0xFF, 0xFF, motor_id, 4, 0x02, address, num_bytes])
    checksum = calc_checksum(packet[2:])
    packet = packet + bytes([checksum])
    ser.reset_input_buffer()
    ser.write(packet)
    time.sleep(0.05)
    resp = ser.read(20)
    if len(resp) >= 8 + num_bytes:
        if num_bytes == 1:
            return resp[9]
        else:
            return resp[9] | (resp[10] << 8)
    return None

def main():
    print("="*60)
    print("COM3 从动臂诊断")
    print("="*60)

    # 先尝试多种波特率 ping ID 1-20
    baudrates = [1000000, 500000, 115200, 9600]
    found_baudrate = None
    found_motors = []

    for br in baudrates:
        print(f"\n尝试波特率 {br}...")
        try:
            ser = serial.Serial('COM3', baudrate=br, timeout=0.15)
            time.sleep(0.3)
            for mid in MOTOR_IDS:
                resp = ping_motor(ser, mid, timeout=0.05)
                if resp and len(resp) >= 4:
                    print(f"  ✓ ID={mid} 响应: {resp.hex()}")
                    found_motors.append(mid)
                    found_baudrate = br
            ser.close()
        except Exception as e:
            print(f"  错误: {e}")

    if not found_motors:
        print(f"\n{'='*60}")
        print("✗ 所有波特率下均未发现电机")
        print("="*60)
        print("\n请检查：")
        print("  1. 5V 外部电源是否已接通（USB 供电不够驱动舵机）")
        print("  2. 舵机驱动板上的 2-pin 跳线是否短接（USB 和电源共地）")
        print("  3. USB 线是否插紧")
        print("  4. 电源指示灯是否亮")
        return

    # 找到电机，读取详细状态
    print(f"\n{'='*60}")
    print(f"使用波特率 {found_baudrate}，发现 {len(found_motors)} 个电机")
    print('='*60)

    ser = serial.Serial('COM3', baudrate=found_baudrate, timeout=0.15)
    time.sleep(0.3)

    for mid in found_motors:
        print(f"\n--- 电机 ID={mid} ---")
        for name, addr, nbytes in REGISTERS:
            val = read_register(ser, mid, addr, nbytes)
            if val is None:
                print(f"  {name} (addr {addr}): 读取失败")
            else:
                if name == "Present_Voltage":
                    print(f"  {name} (addr {addr}): {val/10:.1f}V  (raw={val})")
                elif name == "Torque_Enable":
                    state = "启用(ON)" if val == 1 else "禁用(OFF)"
                    print(f"  {name} (addr {addr}): {state}  (raw={val})")
                elif name == "Status/Error":
                    if val == 0:
                        print(f"  {name} (addr {addr}): 无故障 ✓ (raw={val})")
                    else:
                        faults = []
                        if val & 0x01: faults.append("过热")
                        if val & 0x02: faults.append("过压")
                        if val & 0x04: faults.append("欠压")
                        if val & 0x08: faults.append("过载/堵转")
                        if val & 0x10: faults.append("过流")
                        if val & 0x20: faults.append("过功率")
                        print(f"  {name} (addr {addr}): 故障! {', '.join(faults)} (raw={val:#04x})")
                elif name == "Model_Number":
                    print(f"  {name} (addr {addr}): {val} (0x{val:04X})")
                else:
                    print(f"  {name} (addr {addr}): {val}")

    ser.close()
    print(f"\n{'='*60}")
    print("诊断完成")
    print('='*60)

if __name__ == "__main__":
    main()
