#!/usr/bin/env python3
"""读取舵机6的位置限制寄存器"""
import scservo_sdk as scs

PORT = '/dev/ttyACM0'
BAUDRATE = 1000000
SERVO_ID = 6

# STS3215 寄存器地址
ADDR_MIN_POSITION_LIMIT = 9   # 最小位置限制 (2 bytes)
ADDR_MAX_POSITION_LIMIT = 11  # 最大位置限制 (2 bytes)
ADDR_PRESENT_POSITION = 56    # 当前位置 (2 bytes)

try:
    port_handler = scs.PortHandler(PORT)
    packet_handler = scs.PacketHandler(0)

    if not port_handler.openPort():
        raise RuntimeError(f'无法打开端口 {PORT}')

    if not port_handler.setBaudRate(BAUDRATE):
        raise RuntimeError('无法设置波特率')

    print(f'正在读取舵机 {SERVO_ID} 的位置限制...')

    # 读取 Min_Position_Limit (地址 9)
    min_pos, result, error = packet_handler.read2ByteTxRx(port_handler, SERVO_ID, ADDR_MIN_POSITION_LIMIT)
    if result == 0:
        print(f'  Min_Position_Limit (地址 9): {min_pos}')
    else:
        print(f'  读取 Min_Position_Limit 失败: result={result}, error={error}')

    # 读取 Max_Position_Limit (地址 11)
    max_pos, result, error = packet_handler.read2ByteTxRx(port_handler, SERVO_ID, ADDR_MAX_POSITION_LIMIT)
    if result == 0:
        print(f'  Max_Position_Limit (地址 11): {max_pos}')
    else:
        print(f'  读取 Max_Position_Limit 失败: result={result}, error={error}')

    # 读取当前位置 (地址 56)
    present_pos, result, error = packet_handler.read2ByteTxRx(port_handler, SERVO_ID, ADDR_PRESENT_POSITION)
    if result == 0:
        print(f'  Present_Position (地址 56): {present_pos}')
    else:
        print(f'  读取 Present_Position 失败: result={result}, error={error}')

    print(f'\n分析:')
    print(f'  如果 Max_Position_Limit=4095，说明舵机被限制在标准模式（无法打开夹爪）')
    print(f'  如果 Max_Position_Limit>=5474，说明硬件支持，问题可能在其他地方')

    port_handler.closePort()

except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()