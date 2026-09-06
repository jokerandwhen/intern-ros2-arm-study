#!/usr/bin/env python3
"""读取所有舵机的当前位置（脉冲和角度）"""
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
ADDR_PRESENT_POSITION = 56  # 当前位置 (2 bytes)

try:
    port_handler = scs.PortHandler(PORT)
    packet_handler = scs.PacketHandler(0)

    if not port_handler.openPort():
        raise RuntimeError(f'无法打开端口 {PORT}')

    if not port_handler.setBaudRate(BAUDRATE):
        raise RuntimeError('无法设置波特率')

    print('正在读取所有舵机当前位置...\n')
    print(f'{"关节":<10} {"舵机ID":<8} {"脉冲值":<10} {"硬件角度(°)"}')
    print('-' * 50)

    for joint_name, motor_id in JOINT_ID_MAP.items():
        pos, result, error = packet_handler.read2ByteTxRx(
            port_handler, motor_id, ADDR_PRESENT_POSITION
        )

        if result == 0:
            # joint1-5: 标准12位编码 (0-4095 → 0-360°)
            if joint_name != 'joint6':
                angle = pos * 360.0 / 4096.0
                print(f'{joint_name:<10} {motor_id:<8} {pos:<10} {angle:.2f}')
            # joint6: 使用15位编码，但硬件限制在4095
            else:
                # 暂时按12位计算
                angle = pos * 360.0 / 4096.0
                print(f'{joint_name:<10} {motor_id:<8} {pos:<10} {angle:.2f} (硬件限制4095)')
        else:
            print(f'{joint_name:<10} {motor_id:<8} 读取失败: result={result}, error={error}')

    print('\n注意:')
    print('  joint1-5: 脉冲范围 0-4095，对应 0-360°')
    print('  joint6: 当前硬件限制为4095，需要修改寄存器才能支持更高脉冲值')

    port_handler.closePort()

except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()