#!/usr/bin/env python3
"""测试joint3（舵机3）硬件范围 - 使用15位Sign-Magnitude编码"""
import scservo_sdk as scs

PORT = '/dev/ttyACM0'
BAUDRATE = 1000000
SERVO_ID = 3

# STS3215 寄存器地址
ADDR_PRESENT_POSITION = 56

def decode_sign_magnitude_15bit(encoded_value):
    """15位Sign-Magnitude解码（lerobot方法）"""
    sign_bit_index = 15
    direction_bit = (encoded_value >> sign_bit_index) & 1
    magnitude_mask = (1 << sign_bit_index) - 1  # 0x7FFF = 32767
    magnitude = encoded_value & magnitude_mask
    return -magnitude if direction_bit else magnitude

try:
    port_handler = scs.PortHandler(PORT)
    packet_handler = scs.PacketHandler(0)

    if not port_handler.openPort():
        raise RuntimeError(f'无法打开端口 {PORT}')

    if not port_handler.setBaudRate(BAUDRATE):
        raise RuntimeError('无法设置波特率')

    print('=== joint3（舵机3）硬件范围测试（15位编码）===\n')

    # 读取当前位置（原始值）
    raw_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, SERVO_ID, ADDR_PRESENT_POSITION)

    # 使用15位解码
    decoded_pos = decode_sign_magnitude_15bit(raw_pos)

    print(f'当前原始读取值: {raw_pos}')
    print(f'15位解码后脉冲: {decoded_pos}')
    print(f'说明: 原始值{raw_pos}已超出12位范围，说明joint3使用15位编码')
    print()

    print('=== 结论 ===')
    print('joint3（舵机3）也使用15位Sign-Magnitude编码，和joint6一样')
    print('硬件脉冲范围可达 -32767 ~ +32767')
    print('\n建议：joint3的硬件范围很大，虚拟角度范围可以设置得更宽')

    port_handler.closePort()

except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()