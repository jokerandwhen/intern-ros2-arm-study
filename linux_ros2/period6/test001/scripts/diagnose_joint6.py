#!/usr/bin/env python3
"""关节6硬件诊断与修复脚本"""
import sys
import time

try:
    import scservo_sdk as scs
except ImportError:
    print("[错误] 请先安装 scservo_sdk")
    sys.exit(1)

# STS3215 控制表地址
ADDR_TORQUE_ENABLE = 40
ADDR_GOAL_POSITION = 42
ADDR_PRESENT_POSITION = 56
ADDR_MIN_ANGLE_LIMIT = 9
ADDR_MAX_ANGLE_LIMIT = 11
ADDR_PRESENT_VOLTAGE = 60
ADDR_PRESENT_TEMPERATURE = 61
ADDR_ERROR_STATUS = 50

port_name = '/dev/ttyACM0'
port_handler = scs.PortHandler(port_name)
packet_handler = scs.PacketHandler(0)

if not port_handler.openPort():
    print(f"[错误] 无法打开端口 {port_name}")
    sys.exit(1)

if not port_handler.setBaudRate(1000000):
    print("[错误] 无法设置波特率")
    sys.exit(1)

print("=" * 70)
print("关节6硬件诊断与修复")
print("=" * 70)

servo_id = 6

# 1. 读取错误状态
print("\n[步骤1] 读取错误状态寄存器...")
err_status, result, error = packet_handler.read1ByteTxRx(port_handler, servo_id, ADDR_ERROR_STATUS)
if result == 0:
    print(f"错误状态寄存器值: {err_status} (二进制: {bin(err_status)})")
    if err_status != 0:
        errors = []
        if err_status & 0x01: errors.append("输入电压错误")
        if err_status & 0x02: errors.append("角度限制错误")
        if err_status & 0x04: errors.append("过热错误")
        if err_status & 0x08: errors.append("传感器范围错误")
        if err_status & 0x10: errors.append("电量过低关机")
        if err_status & 0x20: errors.append("指令错误")
        if err_status & 0x40: errors.append("过载错误")
        print(f"检测到错误: {', '.join(errors)}")
    else:
        print("✓ 无硬件错误")
else:
    print(f"读取失败 (result={result})")

# 2. 读取当前位置
print("\n[步骤2] 读取当前位置...")
pos, result, error = packet_handler.read2ByteTxRx(port_handler, servo_id, ADDR_PRESENT_POSITION)
if result == 0:
    angle = pos * 360.0 / 4096.0
    print(f"当前脉冲: {pos}")
    print(f"当前角度: {angle:.1f}°")
else:
    print(f"读取失败")

# 3. 读取角度限制
print("\n[步骤3] 读取角度限制...")
min_limit, result1, _ = packet_handler.read2ByteTxRx(port_handler, servo_id, ADDR_MIN_ANGLE_LIMIT)
max_limit, result2, _ = packet_handler.read2ByteTxRx(port_handler, servo_id, ADDR_MAX_ANGLE_LIMIT)
if result1 == 0 and result2 == 0:
    min_angle = min_limit * 360.0 / 4096.0
    max_angle = max_limit * 360.0 / 4096.0
    print(f"最小脉冲限制: {min_limit} ({min_angle:.1f}°)")
    print(f"最大脉冲限制: {max_limit} ({max_angle:.1f}°)")
    
    if min_limit != 0 or max_limit != 4095:
        print("\n[警告] 角度限制异常！正常应为 0~4095")
        print("这会导致舵机无法正确控制")
else:
    print(f"读取失败")

# 4. 读取扭矩状态
print("\n[步骤4] 读取扭矩状态...")
torque, result, error = packet_handler.read1ByteTxRx(port_handler, servo_id, ADDR_TORQUE_ENABLE)
if result == 0:
    print(f"扭矩状态: {'已启用' if torque else '已禁用'}")
else:
    print(f"读取失败")

# 5. 测试安全位置移动
print("\n[步骤5] 测试移动到安全位置...")
print("首先禁用扭矩，确保安全...")
packet_handler.write1ByteTxRx(port_handler, servo_id, ADDR_TORQUE_ENABLE, 0)
time.sleep(0.1)

print("\n手动测试：尝试移动到中间位置（脉冲2048，对应180°）")
print("这可以帮助判断硬件是否正常...")
test_pulse = 2048
result, error = packet_handler.write2ByteTxRx(port_handler, servo_id, ADDR_GOAL_POSITION, test_pulse)
if result == 0:
    print(f"✓ 写入测试脉冲 {test_pulse} 成功")
    # 启用扭矩
    packet_handler.write1ByteTxRx(port_handler, servo_id, ADDR_TORQUE_ENABLE, 1)
    print("已启用扭矩，观察舵机是否移动...")
    time.sleep(1)
    # 读取实际位置
    pos, result, error = packet_handler.read2ByteTxRx(port_handler, servo_id, ADDR_PRESENT_POSITION)
    if result == 0:
        angle = pos * 360.0 / 4096.0
        print(f"移动后位置: {pos} 脉冲 ({angle:.1f}°)")
        if abs(pos - test_pulse) < 100:
            print("✓ 舵机能正常响应命令")
        else:
            print("✗ 舵机未到达目标位置，可能存在机械卡顿")
else:
    print(f"✗ 写入失败 (result={result})")

# 6. 建议修复方案
print("\n" + "=" * 70)
print("诊断结果与建议：")
print("=" * 70)

if err_status & 0x02:
    print("✗ 检测到角度限制错误")
    print("  原因：尝试发送的脉冲超出硬件限制")
    print("  解决方案：")
    print("  1. 检查robot_commander.py中的OFFSET_REAL_ZERO配置")
    print("  2. 当前配置joint6偏移=269°，虚拟0-90°对应硬件269-359°")
    print("  3. 如果实际硬件范围不同，需要重新标定零点偏移")
    print()
    print("建议运行标定脚本确定正确的偏移量：")
    print("  cd /home/ubuntu/total_internship/period6/test001/scripts")
    print("  python3 auto_calibrate_joint6.py")

if err_status & 0x40:
    print("✗ 检测到过载错误")
    print("  原因：负载过重或机械卡顿")
    print("  解决方案：")
    print("  1. 手动检查夹爪是否能自由移动")
    print("  2. 确认没有异物卡住夹爪")
    print("  3. 如果夹爪物理损坏，需要更换硬件")

port_handler.closePort()

print("\n诊断完成。")