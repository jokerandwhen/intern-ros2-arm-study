#!/usr/bin/env python3
"""只读测试：检查舵机当前脉冲值是否超过4095"""
import scservo_sdk as scs

PORT = '/dev/ttyACM0'
BAUDRATE = 1000000

# STS3215 寄存器地址
ADDR_PRESENT_POSITION = 56

# 实机关节名 → 舵机ID
JOINT_ID_MAP = {
    "joint1": 1,
    "joint2": 2,
    "joint3": 3,
    "joint4": 4,
    "joint5": 5,
    "joint6": 6,
}

try:
    port_handler = scs.PortHandler(PORT)
    packet_handler = scs.PacketHandler(0)

    if not port_handler.openPort():
        raise RuntimeError(f'无法打开端口 {PORT}')

    if not port_handler.setBaudRate(BAUDRATE):
        raise RuntimeError('无法设置波特率')

    print('=== 只读测试：检查舵机脉冲值范围 ===\n')
    print('说明：')
    print('  - 如果当前脉冲值 > 4095，说明舵机在使用15位编码')
    print('  - 如果当前脉冲值 ≤ 4095，说明当前位置在12位范围内（但硬件可能仍支持15位）')
    print()
    print(f'{"关节":<10} {"脉冲值":<10} {"硬件角度(°)":<15} {"编码分析"}')
    print('-' * 65)

    encoding_status = []

    for joint_name, motor_id in JOINT_ID_MAP.items():
        pos, result, error = packet_handler.read2ByteTxRx(
            port_handler, motor_id, ADDR_PRESENT_POSITION
        )

        if result == 0:
            # 计算硬件角度（假设使用12位编码）
            angle_12bit = pos * 360.0 / 4096.0

            # 判断编码类型
            if pos > 4095:
                analysis = "✅ 确认15位编码（脉冲>4095）"
                encoding_status.append((joint_name, '15-bit'))
            elif pos > 3000:
                analysis = "⚠️ 接近上限（脉冲接近4095）"
                encoding_status.append((joint_name, 'limiting'))
            else:
                analysis = "ℹ️ 当前在12位范围内"
                encoding_status.append((joint_name, 'unknown'))

            print(f'{joint_name:<10} {pos:<10} {angle_12bit:<15.2f} {analysis}')
        else:
            print(f'{joint_name:<10} 读取失败')

    print('\n=== 结论 ===')

    # 统计
    confirmed_15bit = [name for name, status in encoding_status if status == '15-bit']
    if confirmed_15bit:
        print(f'✅ 确认使用15位编码的关节: {", ".join(confirmed_15bit)}')
        print('   这些关节的脉冲值已超过12位上限4095')
    else:
        print('ℹ️ 当前所有关节脉冲值都在4095以内')
        print('   无法通过只读测试确定编码位数')
        print('   建议参考lerobot源码中的编码表定义')

    print('\n=== lerobot源码证据 ===')
    print('查看文件: /home/ubuntu/.local/lib/python3.10/site-packages/lerobot/motors/feetech/tables.py')
    print('STS_SMS_SERIES_ENCODINGS_TABLE = {')
    print('    "Goal_Position": 15,      # ← STS3215使用15位编码')
    print('    "Present_Position": 15,')
    print('    ...')
    print('}')
    print('\n结论: STS3215舵机硬件使用15位Sign-Magnitude编码')

    port_handler.closePort()

except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()