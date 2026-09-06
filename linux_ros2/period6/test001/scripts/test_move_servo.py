#!/usr/bin/env python3
"""测试 STS3215 地址42 (Goal Position) 写入 - 小幅移动"""
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

motor_id = 1
print(f"=== 测试舵机 {motor_id} (joint1, 基座) ===")

# 启用扭矩
r, e = ph.write1ByteTxRx(port, motor_id, 40, 1)
print(f"启用扭矩: result={r}, error={e}")
time.sleep(0.2)

# 设置加速度
r, e = ph.write1ByteTxRx(port, motor_id, 41, 30)
print(f"设置加速度: result={r}, error={e}")
time.sleep(0.2)

# 读取当前位置
pos, r, e = ph.read2ByteTxRx(port, motor_id, 56)
print(f"当前位置(addr56): {pos} ({pos*360/4096:.1f}°), result={r}, error={e}")

# 小幅移动 +200 (约18度)
target = min(4095, pos + 200)
print(f"\n写入地址42={target} (移动+18°)...")
r, e = ph.write2ByteTxRx(port, motor_id, 42, target)
print(f"  write2Byte addr42: result={r}, error={e}")
time.sleep(1.5)

# 读取移动后位置
pos2, r, e = ph.read2ByteTxRx(port, motor_id, 56)
print(f"移动后位置(addr56): {pos2} ({pos2*360/4096:.1f}°)")
if abs(pos2 - pos) > 10:
    print("✓ 舵机移动了！地址42是Goal Position")
else:
    print("✗ 舵机没动，地址42可能不是Goal Position")

# 移回原位
print(f"\n移回原位 {pos}...")
r, e = ph.write2ByteTxRx(port, motor_id, 42, pos)
print(f"  write2Byte addr42: result={r}, error={e}")
time.sleep(1.5)

# 禁用扭矩
ph.write1ByteTxRx(port, motor_id, 40, 0)
print("\n已禁用扭矩")

port.closePort()
print("测试完成")
