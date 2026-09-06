#!/usr/bin/env python3
"""
关节6零点偏移标定脚本
目标：确定正确的OFFSET_REAL_ZERO值，让虚拟0-90°能完整映射到硬件范围
"""
import sys
import time

try:
    import scservo_sdk as scs
except ImportError:
    print("[错误] 请先安装 scservo_sdk")
    sys.exit(1)

# STS3215 控制表地址
ADDR_TORQUE_ENABLE = 40
ADDR_GOAL_POSITION = 42
ADDR_PRESENT_POSITION = 56

port_name = '/dev/ttyACM0'
port_handler = scs.PortHandler(port_name)
packet_handler = scs.PacketHandler(0)

if not port_handler.openPort():
    print(f"[错误] 无法打开端口 {port_name}")
    sys.exit(1)

if not port_handler.setBaudRate(1000000):
    print("[错误] 无法设置波特率")
    sys.exit(1)

print("=" * 70)
print("关节6零点偏移标定")
print("=" * 70)

servo_id = 6

# 读取当前位置
pos, result, error = packet_handler.read2ByteTxRx(port_handler, servo_id, ADDR_PRESENT_POSITION)
current_angle = pos * 360.0 / 4096.0

print(f"\n当前位置：")
print(f"  脉冲值：{pos}")
print(f"  硬件角度：{current_angle:.1f}°")

print("\n" + "-" * 70)
print("标定流程：")
print("-" * 70)

# 步骤1：测量夹爪完全闭合时的硬件角度
print("\n[步骤1] 测量夹爪完全闭合位置")
print("请手动将夹爪移动到【完全闭合】状态")
input("完成后按回车继续...")

pos_closed, _, _ = packet_handler.read2ByteTxRx(port_handler, servo_id, ADDR_PRESENT_POSITION)
angle_closed = pos_closed * 360.0 / 4096.0
print(f"完全闭合时硬件角度：{angle_closed:.1f}° (脉冲 {pos_closed})")

# 步骤2：测量夹爪完全张开时的硬件角度
print("\n[步骤2] 测量夹爪完全张开位置")
print("请手动将夹爪移动到【完全张开】状态")
input("完成后按回车继续...")

pos_open, _, _ = packet_handler.read2ByteTxRx(port_handler, servo_id, ADDR_PRESENT_POSITION)
angle_open = pos_open * 360.0 / 4096.0
print(f"完全张开时硬件角度：{angle_open:.1f}° (脉冲 {pos_open})")

# 计算硬件范围
hardware_range = abs(angle_open - angle_closed)
print(f"\n硬件测量范围：{hardware_range:.1f}°")

# 步骤3：确定虚拟零点（闭合状态）对应的硬件角度
print("\n[步骤3] 计算零点偏移")
print("假设：")
print("  - 虚拟0° = 夹爪完全闭合")
print("  - 虚拟90° = 夹爪完全张开")

# 方案A：虚拟0°对应硬件闭合角度
offset_A = angle_closed
print(f"\n方案A（虚拟0°=闭合）：")
print(f"  OFFSET_REAL_ZERO = {offset_A:.2f}°")
print(f"  虚拟0° → 硬件{offset_A:.1f}° → 脉冲{int(offset_A/360*4096)}")
print(f"  虚拟90° → 硬件{offset_A+90:.1f}° → 脉冲{int((offset_A+90)/360*4096)}")

# 方案B：虚拟0°对应硬件张开角度
offset_B = angle_open
print(f"\n方案B（虚拟0°=张开）：")
print(f"  OFFSET_REAL_ZERO = {offset_B:.2f}°")
print(f"  虚拟0° → 硬件{offset_B:.1f}° → 脉冲{int(offset_B/360*4096)}")
print(f"  虚拟90° → 硬件{offset_B+90:.1f}° → 脉冲{int((offset_B+90)/360*4096)}")

# 推荐：基于硬件实际范围
print("\n" + "=" * 70)
print("推荐配置：")
print("=" * 70)

if hardware_range < 100:
    print(f"检测到硬件范围较窄（{hardware_range:.1f}°），建议：")
    print(f"  1. 检查夹爪是否有机械卡顿")
    print(f"  2. 确认夹爪型号是否支持90°开合")
else:
    print(f"硬件范围正常（{hardware_range:.1f}°）")

# 根据用户习惯推荐
print(f"\n请选择虚拟零点定义：")
print(f"  A. 虚拟0° = 闭合，虚拟90° = 张开（推荐）")
print(f"  B. 虚拟0° = 张开，虚拟90° = 闭合")

choice = input("\n请选择 (A/B): ").strip().upper()

if choice == 'A':
    offset = angle_closed
    print(f"\n✓ 已选择方案A")
    print(f"  OFFSET_REAL_ZERO['joint6'] = {offset:.2f}")
elif choice == 'B':
    offset = angle_open
    print(f"\n✓ 已选择方案B")
    print(f"  OFFSET_REAL_ZERO['joint6'] = {offset:.2f}")
else:
    print(f"\n未选择，使用默认方案A")
    offset = angle_closed
    print(f"  OFFSET_REAL_ZERO['joint6'] = {offset:.2f}")

# 测试移动
print("\n[验证] 测试舵机移动...")
print(f"正在测试移动到虚拟45°位置（硬件{offset+45:.1f}°）...")

# 禁用扭矩，写入目标位置，然后启用扭矩观察
packet_handler.write1ByteTxRx(port_handler, servo_id, ADDR_TORQUE_ENABLE, 0)
time.sleep(0.1)

test_angle = offset + 45
test_pulse = int(test_angle / 360.0 * 4096)
packet_handler.write2ByteTxRx(port_handler, servo_id, ADDR_GOAL_POSITION, test_pulse)
time.sleep(0.1)

packet_handler.write1ByteTxRx(port_handler, servo_id, ADDR_TORQUE_ENABLE, 1)
print("已启用扭矩，请观察夹爪是否移动到中间位置（45°）...")
time.sleep(2)

# 读取实际位置
pos_actual, _, _ = packet_handler.read2ByteTxRx(port_handler, servo_id, ADDR_PRESENT_POSITION)
angle_actual = pos_actual * 360.0 / 4096.0

print(f"\n测试结果：")
print(f"  目标位置：{test_pulse} 脉冲 ({test_angle:.1f}°)")
print(f"  实际位置：{pos_actual} 脉冲 ({angle_actual:.1f}°)")

if abs(pos_actual - test_pulse) < 200:
    print("✓ 舵机能正常响应，偏移量配置有效")
else:
    print("✗ 舵机未到达目标位置，可能存在机械问题")

# 清理
packet_handler.write1ByteTxRx(port_handler, servo_id, ADDR_TORQUE_ENABLE, 0)
port_handler.closePort()

print("\n" + "=" * 70)
print("标定完成！")
print("=" * 70)
print(f"\n请在robot_commander.py中更新配置：")
print(f'  "joint6": {offset:.2f}')