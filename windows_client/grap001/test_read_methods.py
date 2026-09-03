"""对比测试两种读取方法"""
import sys, os, time, serial
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接用原始串口测试
PORT = "COM3"
BAUD = 1000000

def build_packet(mid, instr, params=b''):
    length = len(params) + 2
    pkt = bytes([0xFF, 0xFF, mid, length, instr]) + params
    cs = (~sum(pkt[2:]) & 0xFF)
    return pkt + bytes([cs])

ser = serial.Serial(PORT, baudrate=BAUD, timeout=0.2)
time.sleep(0.5)

# 先ping
print("=== Ping测试 ===")
for mid in range(1, 7):
    ser.reset_input_buffer()
    ser.write(build_packet(mid, 0x01))
    time.sleep(0.03)
    r = ser.read(20)
    print(f"  电机{mid}: {'在线' if len(r) >= 6 else '离线'} (收到{len(r)}字节)")

# 方法1: 原始_read2 (read(64), sleep(0.015))
print("\n=== 方法1: read(64) + sleep(0.015) ===")
for mid in range(1, 7):
    ser.reset_input_buffer()
    pkt = build_packet(mid, 0x02, bytes([56, 2]))  # PRESENT_POSITION=56, 2字节
    ser.write(pkt)
    time.sleep(0.015)
    t0 = time.time()
    r = ser.read(64)
    t1 = time.time()
    if len(r) >= 7:
        pos = r[5] | (r[6] << 8)
        print(f"  电机{mid}: pos={pos}  耗时={int((t1-t0)*1000)}ms  收到{len(r)}字节")
    else:
        print(f"  电机{mid}: 失败  耗时={int((t1-t0)*1000)}ms  收到{len(r)}字节")

# 方法2: read(8) + sleep(0.005)
print("\n=== 方法2: read(8) + sleep(0.005) ===")
for mid in range(1, 7):
    ser.reset_input_buffer()
    pkt = build_packet(mid, 0x02, bytes([56, 2]))
    ser.write(pkt)
    time.sleep(0.005)
    t0 = time.time()
    r = ser.read(8)
    t1 = time.time()
    if len(r) >= 8 and r[0] == 0xFF and r[1] == 0xFF:
        pos = r[5] | (r[6] << 8)
        print(f"  电机{mid}: pos={pos}  耗时={int((t1-t0)*1000)}ms  收到{len(r)}字节")
    else:
        print(f"  电机{mid}: 失败  耗时={int((t1-t0)*1000)}ms  收到{len(r)}字节 raw={r.hex() if r else 'empty'}")

# 方法3: 不sleep, 直接读in_waiting
print("\n=== 方法3: 无sleep, 读in_waiting ===")
for mid in range(1, 7):
    ser.reset_input_buffer()
    pkt = build_packet(mid, 0x02, bytes([56, 2]))
    ser.write(pkt)
    # 等待数据（用busy loop，不用sleep）
    waited = 0
    while ser.in_waiting < 8 and waited < 10000:
        waited += 1
    t0 = time.time()
    r = ser.read(ser.in_waiting)
    t1 = time.time()
    if len(r) >= 8 and r[0] == 0xFF and r[1] == 0xFF:
        pos = r[5] | (r[6] << 8)
        print(f"  电机{mid}: pos={pos}  等待={waited}  耗时={int((t1-t0)*1000)}ms  收到{len(r)}字节")
    else:
        print(f"  电机{mid}: 失败  等待={waited}  耗时={int((t1-t0)*1000)}ms  收到{len(r)}字节 raw={r.hex() if r else 'empty'}")

ser.close()
print("\n完成")
