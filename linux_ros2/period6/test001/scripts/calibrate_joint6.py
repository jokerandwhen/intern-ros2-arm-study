#!/usr/bin/env python3
"""
joint6（夹爪）硬件位置标定脚本
用于测定夹爪的实际硬件角度范围
"""
import time
import sys

# STS3215 控制表地址
ADDR_TORQUE_ENABLE = 40
ADDR_GOAL_POSITION = 42
ADDR_PRESENT_POSITION = 56

SERVO_ID = 6  # joint6

def main():
    print("=" * 60)
    print("joint6（夹爪）硬件位置标定")
    print("=" * 60)
    print("\n本脚本会：")
    print("1. 读取当前硬件位置")
    print("2. 移动到几个测试位置")
    print("3. 测定夹爪的实际开合范围")
    print("4. 计算正确的偏移量")
    print()

    try:
        import scservo_sdk as scs
    except ImportError:
        print("[错误] 请先安装 scservo_sdk: pip install scservo_sdk")
        sys.exit(1)

    # 连接舵机
    port_name = '/dev/ttyACM0'
    print(f"[步骤1] 连接串口 {port_name}...")

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

    # 读取当前位置
    print(f"\n[步骤2] 读取当前硬件位置...")
    pos, result, error = packet_handler.read2ByteTxRx(
        port_handler, SERVO_ID, ADDR_PRESENT_POSITION
    )

    if result != 0:
        print("  ✗ 读取失败")
        port_handler.closePort()
        sys.exit(1)

    current_deg = pos * 360.0 / 4096.0
    print(f"  当前硬件位置: {pos} 脉冲 = {current_deg:.1f}°")

    # 测试几个位置
    print(f"\n[步骤3] 测试夹爪开合范围...")
    test_positions = [
        (1000, "小角度（约88°）"),
        (2000, "中角度（约176°）"),
        (3000, "大角度（约264°）"),
        (4000, "接近最大（约352°）"),
    ]

    positions_measured = []

    for target_pulse, desc in test_positions:
        print(f"\n  移动到 {desc}...")
        result, error = packet_handler.write2ByteTxRx(
            port_handler, SERVO_ID, ADDR_GOAL_POSITION, target_pulse
        )
        time.sleep(1.5)

        # 读取实际位置
        pos, result, error = packet_handler.read2ByteTxRx(
            port_handler, SERVO_ID, ADDR_PRESENT_POSITION
        )

        if result == 0:
            actual_deg = pos * 360.0 / 4096.0
            positions_measured.append((target_pulse, pos, actual_deg))
            print(f"    目标: {target_pulse}, 实际: {pos} ({actual_deg:.1f}°)")

            # 让用户观察夹爪状态
            input(f"    请观察夹爪状态，按回车继续...")

    # 计算
    print(f"\n[步骤4] 计算偏移量...")
    print(f"\n测得的位置:")
    for target_pulse, actual_pulse, actual_deg in positions_measured:
        print(f"  目标{target_pulse}: 实际{actual_pulse}脉冲 ({actual_deg:.1f}°)")

    # 建议偏移量
    print(f"\n建议偏移量:")
    print(f"  如果虚拟0°对应夹爪闭合，虚拟90°对应夹爪张开：")
    print(f"  则偏移量 ≈ 测得的最小硬件角度")

    if positions_measured:
        min_pulse = min(p[1] for p in positions_measured)
        max_pulse = max(p[1] for p in positions_measured)
        min_deg = min_pulse * 360.0 / 4096.0
        max_deg = max_pulse * 360.0 / 4096.0

        print(f"\n  最小硬件位置: {min_pulse}脉冲 ({min_deg:.1f}°)")
        print(f"  最大硬件位置: {max_pulse}脉冲 ({max_deg:.1f}°)")
        print(f"  脉冲范围: {max_pulse - min_pulse}")

        # 计算让虚拟0-90°能正常工作的偏移量
        # 虚拟90°应该对应硬件359°（脉冲4095）
        # 所以偏移量 = 359 - 90 = 269°
        # 但如果最大硬件位置只有比如280°，那偏移量应该 = 280 - 90 = 190°

        suggested_offset = max_deg - 90.0
        print(f"\n  建议偏移量: {suggested_offset:.1f}°")
        print(f"  这样虚拟0° → 硬件{suggested_offset:.1f}° → 脉冲{int(suggested_offset/360*4096)}")
        print(f"  虚拟90° → 硬件{suggested_offset+90:.1f}° → 脉冲{int((suggested_offset+90)/360*4096)}")

    port_handler.closePort()
    print(f"\n{'='*60}")
    print("标定完成！")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()