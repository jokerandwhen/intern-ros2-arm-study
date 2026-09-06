#!/usr/bin/env python3
"""测试joint3（舵机3）的硬件物理范围"""
import scservo_sdk as scs
import time

PORT = '/dev/ttyACM0'
BAUDRATE = 1000000
SERVO_ID = 3

# STS3215 寄存器地址
ADDR_TORQUE_ENABLE = 40
ADDR_GOAL_POSITION = 42
ADDR_PRESENT_POSITION = 56
ADDR_MIN_POSITION_LIMIT = 9
ADDR_MAX_POSITION_LIMIT = 11

try:
    port_handler = scs.PortHandler(PORT)
    packet_handler = scs.PacketHandler(0)

    if not port_handler.openPort():
        raise RuntimeError(f'无法打开端口 {PORT}')

    if not port_handler.setBaudRate(BAUDRATE):
        raise RuntimeError('无法设置波特率')

    print('=== joint3（舵机3）硬件范围测试 ===\n')

    # 读取位置限制寄存器
    min_limit, _, _ = packet_handler.read2ByteTxRx(port_handler, SERVO_ID, ADDR_MIN_POSITION_LIMIT)
    max_limit, _, _ = packet_handler.read2ByteTxRx(port_handler, SERVO_ID, ADDR_MAX_POSITION_LIMIT)
    current_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, SERVO_ID, ADDR_PRESENT_POSITION)

    print(f'当前状态:')
    print(f'  Min_Position_Limit: {min_limit} (硬件角度: {min_limit * 360.0 / 4096:.2f}°)')
    print(f'  Max_Position_Limit: {max_limit} (硬件角度: {max_limit * 360.0 / 4096:.2f}°)')
    print(f'  Present_Position: {current_pos} (硬件角度: {current_pos * 360.0 / 4096:.2f}°)')
    print()

    # 测试物理极限（手动移动）
    print('测试方法:')
    print('  1. 请手动移动joint3到最小位置，然后按回车读取')
    input('    移动到最小位置后按回车...')
    min_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, SERVO_ID, ADDR_PRESENT_POSITION)
    min_angle = min_pos * 360.0 / 4096
    print(f'    最小位置: 脉冲={min_pos}, 硬件角度={min_angle:.2f}°')

    print()
    print('  2. 请手动移动joint3到最大位置，然后按回车读取')
    input('    移动到最大位置后按回车...')
    max_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, SERVO_ID, ADDR_PRESENT_POSITION)
    max_angle = max_pos * 360.0 / 4096
    print(f'    最大位置: 脉冲={max_pos}, 硬件角度={max_angle:.2f}°')

    print()
    print('=== joint3硬件物理范围 ===')
    print(f'  硬件角度范围: {min_angle:.2f}° ~ {max_angle:.2f}°')
    print(f'  硬件脉冲范围: {min_pos} ~ {max_pos}')

    # 计算虚拟角度范围（基于OFFSET_REAL_ZERO = 267.98°）
    OFFSET = 267.98
    virtual_min = min_angle - OFFSET
    virtual_max = max_angle - OFFSET
    print(f'\n  虚拟角度范围: {virtual_min:.2f}° ~ {virtual_max:.2f}°')
    print(f'  建议GUI配置: min={virtual_min:.1f}, max={virtual_max:.1f}')

    port_handler.closePort()

except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()