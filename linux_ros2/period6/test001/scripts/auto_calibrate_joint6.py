#!/usr/bin/env python3
"""
joint6（夹爪）自动硬件位置标定
自动测定夹爪的实际硬件角度范围
"""
import time
import sys

# STS3215 控制表地址
ADDR_TORQUE_ENABLE = 40
ADDR_GOAL_POSITION = 42
ADDR_PRESENT_POSITION = 56

SERVO_ID = 6  # joint6

def main():
    print("=" * 70)
    print("joint6（夹爪）自动硬件位置标定")
    print("=" * 70)

    try:
        import scservo_sdk as scs
    except ImportError:
        print("[错误] 请先安装 scservo_sdk: pip install scservo_sdk")
        sys.exit(1)

    # 连接舵机
    port_name = '/dev/ttyACM0'
    print(f"\n[步骤1] 连接串口 {port_name}...")

    port_handler = scs.PortHandler(port_name)
    packet_handler = scs.PacketHandler(0)

    if not port_handler.openPort():
        print("  ✗ 无法打开端口")
        sys.exit(1)

    if not port_handler.setBaudRate(1000000):
        print("  ✗ 无法设置波特率")
        port_handler.closePort()
        sys.exit(1)

    print("  ✓ 已连接")

    # 启用扭矩
    result, error = packet_handler.write1ByteTxRx(
        port_handler, SERVO_ID, ADDR_TORQUE_ENABLE, 1
    )
    if result != 0:
        print("  ✗ 无法启用扭矩")
        port_handler.closePort()
        sys.exit(1)

    print("  ✓ 扭矩已启用")

    # 读取当前硬件位置
    pos, result, error = packet_handler.read2ByteTxRx(
        port_handler, SERVO_ID, ADDR_PRESENT_POSITION
    )

    if result != 0:
        print("  ✗ 读取失败")
        port_handler.closePort()
        sys.exit(1)

    current_deg = pos * 360.0 / 4096.0
    print(f"\n[步骤2] 当前硬件位置: {pos} 脉冲 = {current_deg:.1f}°")

    # 测试完整范围（从最小到最大）
    print(f"\n[步骤3] 测试完整开合范围...")

    test_pulse_values = [100, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000]

    positions_measured = []

    for target_pulse in test_pulse_values:
        # 移动到目标位置
        result, error = packet_handler.write2ByteTxRx(
            port_handler, SERVO_ID, ADDR_GOAL_POSITION, target_pulse
        )
        time.sleep(1.0)  # 等待稳定

        # 读取实际位置
        pos, result, error = packet_handler.read2ByteTxRx(
            port_handler, SERVO_ID, ADDR_PRESENT_POSITION
        )

        if result == 0:
            actual_deg = pos * 360.0 / 4096.0
            positions_measured.append(pos)
            print(f"  目标{target_pulse:4d} → 实际{pos:4d}脉冲 ({actual_deg:6.1f}°)")

    # 分析结果
    print(f"\n[步骤4] 分析结果...")

    min_pulse = min(positions_measured)
    max_pulse = max(positions_measured)
    min_deg = min_pulse * 360.0 / 4096.0
    max_deg = max_pulse * 360.0 / 4096.0

    print(f"\n硬件实测范围:")
    print(f"  最小位置: {min_pulse} 脉冲 ({min_deg:.1f}°)")
    print(f"  最大位置: {max_pulse} 脉冲 ({max_deg:.1f}°)")
    print(f"  脉冲范围: {max_pulse - min_pulse} ({(max_pulse - min_pulse) * 360.0 / 4096.0:.1f}°)")

    # 计算偏移量建议
    print(f"\n偏移量计算:")

    # 方案1：虚拟0°对应硬件最小位置
    offset1 = min_deg
    print(f"\n  方案1：虚拟0° = 硬件最小位置")
    print(f"    偏移量 = {offset1:.1f}°")
    print(f"    虚拟0° → 硬件{offset1:.1f}° → 脉冲{int(offset1/360*4096)}")
    print(f"    虚拟{(max_deg - offset1):.1f}° → 硬件{max_deg:.1f}° → 脉冲{max_pulse}")

    # 方案2：让虚拟角度能覆盖0-90°
    # 虚拟90°应该对应硬件最大位置
    offset2 = max_deg - 90.0
    print(f"\n  方案2：虚拟90° = 硬件最大位置")
    print(f"    偏移量 = {offset2:.1f}°")
    print(f"    虚拟0° → 硬件{offset2:.1f}° → 脉冲{int(offset2/360*4096)}")
    print(f"    虚拟90° → 硬件{max_deg:.1f}° → 脉冲{max_pulse}")

    # 推荐
    print(f"\n{'='*70}")
    print("推荐方案：")
    print(f"  如果希望虚拟0-90°能完整覆盖硬件范围：")
    print(f"  → 偏移量设为 {offset2:.1f}°")
    print(f"  → 修改 robot_commander.py 中的 OFFSET_REAL_ZERO['joint6']")
    print(f"{'='*70}")

    # 禁用扭矩
    packet_handler.write1ByteTxRx(
        port_handler, SERVO_ID, ADDR_TORQUE_ENABLE, 0
    )

    port_handler.closePort()

if __name__ == '__main__':
    main()