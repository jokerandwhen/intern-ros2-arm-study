#!/usr/bin/env python3
"""
修复舵机角度限制，退出电机模式
将所有舵机的角度限制设置为 0~4095（正常舵机模式）
"""
import time
import sys

# STS3215 控制表地址
ADDR_TORQUE_ENABLE = 40
ADDR_MIN_ANGLE_LIMIT = 9    # Min_Position_Limit
ADDR_MAX_ANGLE_LIMIT = 11   # Max_Position_Limit

# 目标舵机ID列表
SERVO_IDS = [1, 2, 3, 4, 5, 6]

def main():
    print("=" * 60)
    print("修复舵机角度限制（退出电机模式）")
    print("=" * 60)

    try:
        import scservo_sdk as scs
    except ImportError:
        print("\n[错误] 请先安装 scservo_sdk: pip install scservo_sdk")
        sys.exit(1)

    # 连接舵机
    port_name = '/dev/ttyACM0'
    print(f"\n[步骤1] 连接串口 {port_name}...")

    port_handler = scs.PortHandler(port_name)
    packet_handler = scs.PacketHandler(0)

    if not port_handler.openPort():
        print(f"  ✗ 无法打开端口")
        sys.exit(1)

    if not port_handler.setBaudRate(1000000):
        print(f"  ✗ 无法设置波特率")
        port_handler.closePort()
        sys.exit(1)

    print(f"  ✓ 已连接")

    print(f"\n[步骤2] 修复所有舵机角度限制...")

    for servo_id in SERVO_IDS:
        print(f"\n  舵机 ID {servo_id}:")

        # 1. 禁用扭矩
        result, error = packet_handler.write1ByteTxRx(
            port_handler, servo_id, ADDR_TORQUE_ENABLE, 0
        )
        if result != 0:
            print(f"    ✗ 禁用扭矩失败")
            continue
        print(f"    ✓ 扭矩已禁用")
        time.sleep(0.05)

        # 2. 读取当前限制
        min_val, result1, _ = packet_handler.read2ByteTxRx(
            port_handler, servo_id, ADDR_MIN_ANGLE_LIMIT
        )
        max_val, result2, _ = packet_handler.read2ByteTxRx(
            port_handler, servo_id, ADDR_MAX_ANGLE_LIMIT
        )

        if result1 == 0 and result2 == 0:
            print(f"    当前限制: {min_val} ~ {max_val}")
        else:
            print(f"    读取限制失败")

        # 3. 写入正确限制（0~4095）
        result1, _ = packet_handler.write2ByteTxRx(
            port_handler, servo_id, ADDR_MIN_ANGLE_LIMIT, 0
        )
        time.sleep(0.05)
        result2, _ = packet_handler.write2ByteTxRx(
            port_handler, servo_id, ADDR_MAX_ANGLE_LIMIT, 4095
        )
        time.sleep(0.05)

        if result1 == 0 and result2 == 0:
            print(f"    ✓ 已设置为 0 ~ 4095")
        else:
            print(f"    ✗ 写入失败")

        # 4. 验证
        min_val, result1, _ = packet_handler.read2ByteTxRx(
            port_handler, servo_id, ADDR_MIN_ANGLE_LIMIT
        )
        max_val, result2, _ = packet_handler.read2ByteTxRx(
            port_handler, servo_id, ADDR_MAX_ANGLE_LIMIT
        )

        if min_val == 0 and max_val == 4095:
            print(f"    ✓ 验证成功: {min_val} ~ {max_val}")
        else:
            print(f"    ✗ 验证失败: {min_val} ~ {max_val}")

    port_handler.closePort()

    print(f"\n{'='*60}")
    print("修复完成！")
    print("请断电重启机械臂，然后再运行诊断脚本验证")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()