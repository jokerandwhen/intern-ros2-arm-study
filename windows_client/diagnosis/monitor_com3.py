"""
监听 COM3 原始数据 + 长 ping 测试
"""
import serial, time

ser = serial.Serial('COM3', baudrate=1000000, timeout=0.5)
time.sleep(0.5)

# 1. 监听 3 秒看有没有任何自发数据
ser.reset_input_buffer()
print("监听 COM3 (1Mbps) 3秒...")
end = time.time() + 3
total = 0
while time.time() < end:
    n = ser.in_waiting
    if n > 0:
        data = ser.read(n)
        total += len(data)
        print(f"  收到 {len(data)} 字节: {data.hex()}")
    time.sleep(0.1)
if total == 0:
    print("  3秒内无任何自发数据")

# 2. 逐个 ping ID 1-10, 长 200ms 超时
print()
print("逐个 ping (超时 200ms)...")
for mid in range(1, 11):
    packet = bytes([0xFF, 0xFF, mid, 2, 0x01])
    checksum = (~sum(packet[2:]) & 0xFF)
    packet = packet + bytes([checksum])
    ser.reset_input_buffer()
    ser.write(packet)
    time.sleep(0.2)
    resp = ser.read(100)
    if resp and len(resp) >= 4:
        print(f"  ID={mid}: 收到 {len(resp)} 字节: {resp.hex()}")
    else:
        print(f"  ID={mid}: 无响应")

# 3. 检查 TX 是否正常（回环测试）
# 有些半双工板子会把自己的发送数据也回显
print()
print("回环检查：发送后是否能看到自己的数据...")
ser.reset_input_buffer()
packet = bytes([0xFF, 0xFF, 1, 2, 0x01])
checksum = (~sum(packet[2:]) & 0xFF)
packet = packet + bytes([checksum])
ser.write(packet)
time.sleep(0.05)
resp = ser.read(100)
if resp and len(resp) >= 6:
    print(f"  回环数据: {resp.hex()}")
    print("  说明 CH343 芯片和收发器工作正常，但舵机没有回应")
    print("  可能原因：外部电源未接 / 舵机驱动板故障 / 舵机ID不在1-10范围")
else:
    print(f"  无回环数据，收到 {len(resp)} 字节")
    print("  说明 CH343 收发可能有问题，或者半双工方向控制未生效")

ser.close()
print("\n完成")
