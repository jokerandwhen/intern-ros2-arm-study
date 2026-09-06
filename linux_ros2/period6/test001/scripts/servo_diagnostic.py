#!/usr/bin/env python3
"""
SO-ARM101 舵机总线诊断脚本
检测：ID冲突、波特率、通信质量、舵机状态
"""
import time
import sys

# 尝试不同的波特率
BAUDRATES = [1000000, 500000, 115200, 57600, 38400]

# STS3215 控制表地址
ADDR_ID = 3                    # 舵机ID
ADDR_BAUDRATE = 4              # 波特率
ADDR_RETURN_DELAY = 5          # 返回延迟时间
ADDR_MIN_ANGLE_LIMIT = 9       # 最小角度限制（EPROM）
ADDR_MAX_ANGLE_LIMIT = 11      # 最大角度限制（EPROM）
ADDR_TORQUE_ENABLE = 40        # 扭矩启用
ADDR_MOVING_ACC = 41           # 加速度
ADDR_GOAL_POSITION = 42        # 目标位置
ADDR_PRESENT_POSITION = 56     # 当前位置
ADDR_PRESENT_VOLTAGE = 60      # 当前电压
ADDR_PRESENT_TEMPERATURE = 61  # 当前温度
ADDR_MOVING_STATUS = 66        # 移动状态

# 波特率值映射
BAUDRATE_MAP = {
    0: 9600,
    1: 57600,
    2: 115200,
    3: 1000000,
    4: 2000000,
    5: 3000000,
}

def scan_bus(port_handler, packet_handler, baudrate):
    """扫描总线上的所有舵机"""
    found_ids = []

    print(f"\n  扫描波特率 {baudrate}...")

    # 扫描常见ID范围（1-20）
    for servo_id in range(1, 21):
        try:
            # 使用read2ByteTxRx读取位置来检测舵机（比ping更可靠）
            pos, result, error = packet_handler.read2ByteTxRx(
                port_handler, servo_id, ADDR_PRESENT_POSITION
            )
            if result == 0 and error == 0:
                found_ids.append(servo_id)
        except Exception:
            pass

    return found_ids

def read_servo_info(port_handler, packet_handler, servo_id):
    """读取单个舵机的详细信息"""
    info = {}

    # 读取ID
    val, result, error = packet_handler.read1ByteTxRx(port_handler, servo_id, ADDR_ID)
    if result == 0:
        info['id'] = val

    # 读取波特率设置
    val, result, error = packet_handler.read1ByteTxRx(port_handler, servo_id, ADDR_BAUDRATE)
    if result == 0:
        info['baudrate_setting'] = val
        info['baudrate'] = BAUDRATE_MAP.get(val, f"未知({val})")

    # 读取电压
    val, result, error = packet_handler.read1ByteTxRx(port_handler, servo_id, ADDR_PRESENT_VOLTAGE)
    if result == 0:
        info['voltage'] = val / 10.0  # 单位：0.1V

    # 读取温度
    val, result, error = packet_handler.read1ByteTxRx(port_handler, servo_id, ADDR_PRESENT_TEMPERATURE)
    if result == 0:
        info['temperature'] = val  # 单位：摄氏度

    # 读取扭矩状态
    val, result, error = packet_handler.read1ByteTxRx(port_handler, servo_id, ADDR_TORQUE_ENABLE)
    if result == 0:
        info['torque_enabled'] = val

    # 读取角度限制
    min_val, result1, _ = packet_handler.read2ByteTxRx(port_handler, servo_id, ADDR_MIN_ANGLE_LIMIT)
    max_val, result2, _ = packet_handler.read2ByteTxRx(port_handler, servo_id, ADDR_MAX_ANGLE_LIMIT)
    if result1 == 0 and result2 == 0:
        info['min_angle_pulse'] = min_val
        info['max_angle_pulse'] = max_val
        info['min_angle'] = min_val * 360.0 / 4096.0
        info['max_angle'] = max_val * 360.0 / 4096.0

    # 读取当前位置
    val, result, error = packet_handler.read2ByteTxRx(port_handler, servo_id, ADDR_PRESENT_POSITION)
    if result == 0:
        info['position_pulse'] = val
        info['position'] = val * 360.0 / 4096.0

    return info

def test_communication_quality(port_handler, packet_handler, servo_id, tests=10):
    """测试通信质量"""
    success = 0
    timeouts = 0
    errors = 0

    for _ in range(tests):
        try:
            # 使用读取位置来测试通信
            _, result, error = packet_handler.read2ByteTxRx(
                port_handler, servo_id, ADDR_PRESENT_POSITION
            )
            if result == 0 and error == 0:
                success += 1
            elif result == 2:  # COMM_RX_TIMEOUT
                timeouts += 1
            else:
                errors += 1
        except Exception:
            errors += 1
        time.sleep(0.01)

    return {
        'success_rate': success / tests * 100,
        'timeouts': timeouts,
        'errors': errors
    }

def main():
    print("=" * 60)
    print("SO-ARM101 舵机总线诊断工具")
    print("=" * 60)

    try:
        import scservo_sdk as scs
    except ImportError:
        print("\n[错误] 请先安装 scservo_sdk: pip install scservo_sdk")
        sys.exit(1)

    # 查找可用端口
    port_name = '/dev/ttyACM0'

    print(f"\n[步骤1] 查找串口设备...")
    import os
    if os.path.exists(port_name):
        print(f"  ✓ 找到串口: {port_name}")
    else:
        # 尝试其他端口
        for i in range(10):
            test_port = f'/dev/ttyACM{i}'
            if os.path.exists(test_port):
                port_name = test_port
                print(f"  ✓ 找到串口: {port_name}")
                break
        else:
            print(f"  ✗ 未找到串口设备")
            sys.exit(1)

    print(f"\n[步骤2] 扫描舵机总线...")

    # 创建通信对象
    port_handler = scs.PortHandler(port_name)
    packet_handler = scs.PacketHandler(0)

    all_found_ids = {}
    working_baudrate = None

    for baudrate in BAUDRATES:
        if not port_handler.openPort():
            print(f"  ✗ 无法打开端口")
            sys.exit(1)

        if not port_handler.setBaudRate(baudrate):
            print(f"  ✗ 无法设置波特率 {baudrate}")
            port_handler.closePort()
            continue

        found = scan_bus(port_handler, packet_handler, baudrate)

        port_handler.closePort()

        if found:
            all_found_ids[baudrate] = found
            working_baudrate = baudrate
            print(f"  ✓ 波特率 {baudrate}: 找到 {len(found)} 个舵机 - ID: {found}")

    if not all_found_ids:
        print("\n[错误] 未检测到任何舵机！")
        print("可能原因：")
        print("  1. 供电不足（请使用 >= 3A 的电源适配器）")
        print("  2. 波特率不在常见范围内")
        print("  3. 串口线未正确连接")
        sys.exit(1)

    # 检查多波特率情况（可能有问题）
    if len(all_found_ids) > 1:
        print(f"\n[警告] 检测到多个波特率都有舵机响应！")
        print("  这可能表示：")
        print("  1. 不同舵机使用了不同的波特率（需要统一）")
        print("  2. 总线干扰导致误响应")

    # 使用第一个工作的波特率继续
    working_baudrate = list(all_found_ids.keys())[0]

    print(f"\n[步骤3] 详细诊断每个舵机...")

    port_handler.openPort()
    port_handler.setBaudRate(working_baudrate)

    for baudrate, ids in all_found_ids.items():
        port_handler.setBaudRate(baudrate)

        for servo_id in ids:
            print(f"\n  {'='*50}")
            print(f"  舵机 ID: {servo_id}")
            print(f"  {'='*50}")

            # 读取详细信息
            info = read_servo_info(port_handler, packet_handler, servo_id)

            # 显示基本信息
            baudrate = info.get('baudrate', 'N/A')
            baudrate_setting = info.get('baudrate_setting', 'N/A')
            voltage = info.get('voltage', 'N/A')
            temp = info.get('temperature', 'N/A')
            torque = '已启用' if info.get('torque_enabled') else '已禁用'

            min_angle = info.get('min_angle', 'N/A')
            max_angle = info.get('max_angle', 'N/A')
            min_pulse = info.get('min_angle_pulse', 'N/A')
            max_pulse = info.get('max_angle_pulse', 'N/A')

            position = info.get('position', 'N/A')
            position_pulse = info.get('position_pulse', 'N/A')

            print(f"  波特率设置: {baudrate} (寄存器值: {baudrate_setting})")
            print(f"  当前电压: {voltage} V")
            print(f"  当前温度: {temp} °C")
            print(f"  扭矩状态: {torque}")

            # 角度限制和位置（格式化数值或显示N/A）
            if isinstance(min_angle, float):
                print(f"  角度限制: {min_angle:.1f}° ~ {max_angle:.1f}° (脉冲: {min_pulse} ~ {max_pulse})")
            else:
                print(f"  角度限制: {min_angle} ~ {max_angle} (脉冲: {min_pulse} ~ {max_pulse})")

            if isinstance(position, float):
                print(f"  当前位置: {position:.1f}° (脉冲: {position_pulse})")
            else:
                print(f"  当前位置: {position} (脉冲: {position_pulse})")

            # 角度限制警告
            min_ang = info.get('min_angle', 0)
            max_ang = info.get('max_angle', 0)
            min_pulse = info.get('min_angle_pulse', 0)
            max_pulse = info.get('max_angle_pulse', 0)

            if min_pulse != 0 or max_pulse != 4095:
                print(f"  [警告] 角度限制异常！正常应为 0~4095")
                print(f"         当前设置会导致舵机进入电机模式（多圈旋转）")
                print(f"         机械臂关节应使用舵机模式（单圈0~4095）")

            # 检测脉冲值是否超过4095（电机模式）
            position_pulse = info.get('position_pulse', 0)
            if position_pulse > 4095:
                print(f"  [严重警告] 当前脉冲值 {position_pulse} > 4095！")
                print(f"             舵机处于电机模式（多圈旋转），不是舵机模式！")
                print(f"             需要修复角度限制并断电重启")

            # 电压警告
            voltage = info.get('voltage', 0)
            if voltage < 10.0:
                print(f"  [警告] 电压过低 ({voltage}V < 10V)，可能导致抖动！")
            elif voltage < 11.0:
                print(f"  [注意] 电压偏低 ({voltage}V)，建议检查电源")

            # 温度警告
            temp = info.get('temperature', 0)
            if temp > 70:
                print(f"  [警告] 温度过高 ({temp}°C > 70°C)，可能触发过热保护！")

            # 测试通信质量
            print(f"\n  通信质量测试 (10次):")
            quality = test_communication_quality(port_handler, packet_handler, servo_id)
            print(f"    成功率: {quality['success_rate']:.0f}%")
            print(f"    超时: {quality['timeouts']} 次")
            print(f"    错误: {quality['errors']} 次")

            if quality['success_rate'] < 80:
                print(f"    [警告] 通信质量差，可能存在硬件问题！")

    # 检查ID冲突
    print(f"\n[步骤4] 检查ID冲突...")
    all_ids = []
    for ids in all_found_ids.values():
        all_ids.extend(ids)

    duplicates = [id for id in set(all_ids) if all_ids.count(id) > 1]
    if duplicates:
        print(f"  [严重错误] 检测到ID冲突: {duplicates}")
        print("  解决方法：使用舵机配置软件修改ID，确保每个舵机ID唯一")
    else:
        print(f"  ✓ 未检测到ID冲突")

    # 预期ID检查
    expected_ids = [1, 2, 3, 4, 5, 6]
    missing = [id for id in expected_ids if id not in all_ids]
    unexpected = [id for id in all_ids if id not in expected_ids]

    if missing:
        print(f"\n  [注意] 缺少预期舵机 ID: {missing}")
    if unexpected:
        print(f"\n  [注意] 检测到额外舵机 ID: {unexpected}")

    port_handler.closePort()

    print(f"\n{'='*60}")
    print("诊断完成！")
    print(f"{'='*60}")

    # 总结建议
    print("\n总结与建议:")
    if working_baudrate != 1000000:
        print(f"  1. 波特率不是默认的1M，当前: {working_baudrate}")
        print(f"     建议：统一所有舵机波特率为 1,000,000")

    if duplicates:
        print(f"  2. 存在ID冲突，必须修复！")

    if voltage and voltage < 11.0:
        print(f"  3. 供电不足，建议使用 >= 3A 的电源适配器")

if __name__ == '__main__':
    main()