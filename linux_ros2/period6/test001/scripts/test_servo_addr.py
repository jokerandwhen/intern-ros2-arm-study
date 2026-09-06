#!/usr/bin/env python3
"""测试 STS3215 舵机的实际 Goal Position 地址"""
import sys
import time
import scservo_sdk as scs

port = scs.PortHandler('/dev/ttyACM0')
ph = scs.PacketHandler(0)

if not port.openPort():
    print("无法打开端口")
    sys.exit(1)
if not port.setBaudRate(1000000):
    print("无法设置波特率")
    sys.exit(1)

print("已连接串口\n")

for motor_id in [1, 2, 6]:
    print(f"=== 舵机 {motor_id} ===")
    # 读取地址56 (Present Position - 当前位置)
    pos56, r1, e1 = ph.read2ByteTxRx(port, motor_id, 56)
    print(f"  读地址56(Present Pos): value={pos56}, result={r1}, error={e1}")
    # 读取地址30 (假设的Goal Position)
    val30, r2, e2 = ph.read2ByteTxRx(port, motor_id, 30)
    print(f"  读地址30(假设Goal): value={val30}, result={r2}, error={e2}")
    # 读取地址42 (STS3215真正的Goal Position)
    val42, r3, e3 = ph.read2ByteTxRx(port, motor_id, 42)
    print(f"  读地址42(STS3215 Goal): value={val42}, result={r3}, error={e3}")

    if r1 == 0:
        # 尝试写入地址42，值=当前位置(舵机应该不动)
        rw, ew = ph.write2ByteTxRx(port, motor_id, 42, pos56)
        print(f"  写地址42={pos56}(当前位置): result={rw}, error={ew}")
        time.sleep(0.3)
        # 尝试写入地址30
        rw2, ew2 = ph.write2ByteTxRx(port, motor_id, 30, pos56)
        print(f"  写地址30={pos56}: result={rw2}, error={ew2}")
        time.sleep(0.3)
    print()

port.closePort()
print("测试完成")
