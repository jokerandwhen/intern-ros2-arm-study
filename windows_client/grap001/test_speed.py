"""测试高速读取速度"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arm_controller import SoArmController

arm = SoArmController(port="COM3")
arm.connect()
time.sleep(0.3)

# 测试高速读取
print("\n测试高速读取 (10次)...")
times = []
for i in range(10):
    t0 = time.time()
    pos = arm.read_all_positions_fast()
    t1 = time.time()
    times.append((t1-t0)*1000)
    print(f"  第{i+1}次: {(t1-t0)*1000:.1f}ms  pos={pos}")

avg = sum(times)/len(times)
print(f"\n平均读取时间: {avg:.1f}ms")
print(f"理论最大帧率: {1000/avg:.0f} Hz")
print(f"实际录制帧率(20Hz): {'可行' if avg < 50 else '可能不够快'}")

arm.disconnect()
