#!/usr/bin/env python3
"""恢复所有舵机的位置限制寄存器到默认值0~4095"""
import scservo_sdk as scs
import time

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
ADDR_TORQUE_ENABLE = 40
ADDR_MIN_POSITION_LIMIT = 9
ADDR_MAX_POSITION_LIMIT = 11

try:
    port_handler = scs.PortHandler(PORT)
    packet_handler = scs.PacketHandler(0)

    if not port_handler.openPort():
        raise RuntimeError(f'无法打开端口 {PORT}')

    if not port_handler.setBaudRate(BAUDRATE):
        raise RuntimeError('无法设置波特率')

    print('=== 恢复舵机位置限制到默认值 ===\n')
    print('目标: 将所有舵机的位置限制恢复到 0~4095（12位编码）\n')

    for joint_name, motor_id in JOINT_ID_MAP.items():
        print(f'正在恢复 {joint_name} (ID={motor_id})...')

        # 禁用扭矩
        packet_handler.write1ByteTxRx(port_handler, motor_id, ADDR_TORQUE_ENABLE, 0)
        time.sleep(0.1)

        # 写入默认限制值
        packet_handler.write2ByteTxRx(port_handler, motor_id, ADDR_MIN_POSITION_LIMIT, 0)
        packet_handler.write2ByteTxRx(port_handler, motor_id, ADDR_MAX_POSITION_LIMIT, 4095)
        time.sleep(0.1)

        # 验证写入
        min_limit, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_MIN_POSITION_LIMIT)
        max_limit, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_MAX_POSITION_LIMIT)

        print(f'  ✓ 已恢复: Min={min_limit}, Max={max_limit}')

    print('\n=== 验证结果 ===')
    print(f'{"关节":<10} {"Min_Limit":<12} {"Max_Limit":<12}')
    print('-' * 40)

    for joint_name, motor_id in JOINT_ID_MAP.items():
        min_limit, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_MIN_POSITION_LIMIT)
        max_limit, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_MAX_POSITION_LIMIT)
        print(f'{joint_name:<10} {min_limit:<12} {max_limit:<12}')

    print('\n✅ 所有舵机位置限制已恢复到默认值（0~4095）')

    port_handler.closePort()

except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()