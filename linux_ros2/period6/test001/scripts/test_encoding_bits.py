#!/usr/bin/env python3
"""实测舵机编码位数 - 尝试写入超过4095的脉冲值"""
import scservo_sdk as scs
import time

PORT = '/dev/ttyACM0'
BAUDRATE = 1000000

# STS3215 寄存器地址
ADDR_TORQUE_ENABLE = 40
ADDR_GOAL_POSITION = 42
ADDR_PRESENT_POSITION = 56
ADDR_MIN_POSITION_LIMIT = 9
ADDR_MAX_POSITION_LIMIT = 11

def test_servo_encoding(motor_id, motor_name):
    """测试单个舵机的编码位数"""
    print(f'\n=== 测试 {motor_name} (ID={motor_id}) ===')

    try:
        port_handler = scs.PortHandler(PORT)
        packet_handler = scs.PacketHandler(0)

        if not port_handler.openPort():
            raise RuntimeError(f'无法打开端口 {PORT}')

        if not port_handler.setBaudRate(BAUDRATE):
            raise RuntimeError('无法设置波特率')

        # 1. 读取当前位置
        current_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
        print(f'当前脉冲值: {current_pos}')

        # 2. 修改位置限制到10000
        print('扩展位置限制到 0~10000...')
        packet_handler.write1ByteTxRx(port_handler, motor_id, ADDR_TORQUE_ENABLE, 0)  # 禁用扭矩
        time.sleep(0.1)
        packet_handler.write2ByteTxRx(port_handler, motor_id, ADDR_MIN_POSITION_LIMIT, 0)
        packet_handler.write2ByteTxRx(port_handler, motor_id, ADDR_MAX_POSITION_LIMIT, 10000)
        time.sleep(0.1)

        # 验证修改
        max_limit, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_MAX_POSITION_LIMIT)
        print(f'已修改限制: Max={max_limit}')

        # 3. 启用扭矩
        packet_handler.write1ByteTxRx(port_handler, motor_id, ADDR_TORQUE_ENABLE, 1)
        time.sleep(0.1)

        # 4. 测试写入脉冲值4500（超过12位上限4095）
        test_pulse = 4500
        print(f'\n尝试写入脉冲值: {test_pulse}（超过4095）')
        result, error = packet_handler.write2ByteTxRx(port_handler, motor_id, ADDR_GOAL_POSITION, test_pulse)

        if result == 0:
            print(f'✓ 写入成功！等待2秒让舵机移动...')
            time.sleep(2)

            # 5. 读取实际位置
            actual_pos, _, _ = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
            print(f'实际位置: {actual_pos}')

            if abs(actual_pos - test_pulse) < 50:  # 允许误差50脉冲
                print('✅ 舵机成功到达目标位置（支持超过4095）')
                encoding_result = '15位编码（支持>4095）'
            else:
                print(f'⚠️ 舵机位置偏差较大（目标{test_pulse}，实际{actual_pos}）')
                encoding_result = '编码异常'
        else:
            print(f'❌ 写入失败: result={result}, error={error}')
            encoding_result = '12位编码（不支持>4095）'

        # 6. 恢复原位置
        print(f'\n恢复到原位置: {current_pos}')
        packet_handler.write2ByteTxRx(port_handler, motor_id, ADDR_GOAL_POSITION, current_pos)
        time.sleep(2)

        port_handler.closePort()
        return encoding_result

    except Exception as e:
        print(f'错误: {e}')
        return '测试失败'

# 测试所有舵机
print('=== 舵机编码位数实测 ===')
print('目标: 验证舵机是否支持超过4095的脉冲值')

results = {}
for motor_id, motor_name in [(1, 'joint1'), (3, 'joint3'), (6, 'joint6')]:
    results[motor_name] = test_servo_encoding(motor_id, motor_name)

print('\n' + '='*60)
print('测试结果汇总:')
for motor_name, result in results.items():
    print(f'  {motor_name}: {result}')
print('='*60)