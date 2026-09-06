#!/usr/bin/env python3
"""检查所有舵机的位置限制寄存器"""
import scservo_sdk as scs

PORT = '/dev/ttyACM0'
BAUDRATE = 1000000

# 实机关节名 → 舵机ID
JOINT_ID_MAP = {
    "joint1": 1,
    "joint2": 2,
    "joint3": 3,
    "joint4": 4,
    "joint5": 5,
    "joint6": 6,
}

# STS3215 寄存器地址
ADDR_MIN_POSITION_LIMIT = 9
ADDR_MAX_POSITION_LIMIT = 11
ADDR_PRESENT_POSITION = 56

try:
    port_handler = scs.PortHandler(PORT)
    packet_handler = scs.PacketHandler(0)

    if not port_handler.openPort():
        raise RuntimeError(f'无法打开端口 {PORT}')

    if not port_handler.setBaudRate(BAUDRATE):
        raise RuntimeError('无法设置波特率')

    print('=== 所有舵机位置限制检查 ===\n')
    print(f'{"关节":<10} {"ID":<5} {"Min_Limit":<12} {"Max_Limit":<12} {"当前位置":<12} {"状态"}')
    print('-' * 75)

    for joint_name, motor_id in JOINT_ID_MAP.items():
        min_limit, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_MIN_POSITION_LIMIT)
        max_limit, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_MAX_POSITION_LIMIT)
        current_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)

        # 检查是否需要修改限制
        status = ''
        if max_limit < 5000 and joint_name in ['joint3', 'joint6']:
            status = '⚠️ 需要扩大限制'
        elif max_limit == 4095:
            status = '⚠️ 标准12位限制'
        else:
            status = '✓ 已扩展'

        print(f'{joint_name:<10} {motor_id:<5} {min_limit:<12} {max_limit:<12} {current_pos:<12} {status}')

    print()
    print('说明:')
    print('  - 如果Max_Limit=4095，说明舵机被限制在标准12位模式')
    print('  - joint3和joint6可能需要扩展到6000+才能完全运动')
    print('  - 需要修改位置限制寄存器才能使用15位编码的全范围')

    port_handler.closePort()

except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()