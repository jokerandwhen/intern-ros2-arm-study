#!/usr/bin/env python3
"""检查关节3和关节6的硬件状态"""
import sys

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
ADDR_MOVING_STATUS = 66
ADDR_ERROR_STATUS = 50  # 错误状态寄存器

port_name = '/dev/ttyACM0'
port_handler = scs.PortHandler(port_name)
packet_handler = scs.PacketHandler(0)

if not port_handler.openPort():
    print(f"[错误] 无法打开端口 {port_name}")
    sys.exit(1)

if not port_handler.setBaudRate(1000000):
    print("[错误] 无法设置波特率")
    sys.exit(1)

print("=" * 60)
print("关节3和关节6硬件状态检查")
print("=" * 60)

for servo_id in [3, 6]:
    print(f"\n--- 舵机 {servo_id} ---")
    
    # 读取扭矩状态
    torque, result, error = packet_handler.read1ByteTxRx(port_handler, servo_id, ADDR_TORQUE_ENABLE)
    if result == 0:
        print(f"扭矩状态: {'已启用' if torque else '已禁用'}")
    else:
        print(f"扭矩状态: 读取失败 (result={result})")
    
    # 读取当前位置
    pos, result, error = packet_handler.read2ByteTxRx(port_handler, servo_id, ADDR_PRESENT_POSITION)
    if result == 0:
        angle = pos * 360.0 / 4096.0
        print(f"当前位置: {pos} 脉冲 ({angle:.1f}°)")
    else:
        print(f"当前位置: 读取失败")
    
    # 读取角度限制
    min_limit, result1, _ = packet_handler.read2ByteTxRx(port_handler, servo_id, ADDR_MIN_ANGLE_LIMIT)
    max_limit, result2, _ = packet_handler.read2ByteTxRx(port_handler, servo_id, ADDR_MAX_ANGLE_LIMIT)
    if result1 == 0 and result2 == 0:
        min_angle = min_limit * 360.0 / 4096.0
        max_angle = max_limit * 360.0 / 4096.0
        print(f"角度限制: {min_limit}~{max_limit} 脉冲 ({min_angle:.1f}°~{max_angle:.1f}°)")
        if min_limit != 0 or max_limit != 4095:
            print(f"  [警告] 角度限制异常！正常应为 0~4095")
    
    # 读取电压
    voltage, result, error = packet_handler.read1ByteTxRx(port_handler, servo_id, ADDR_PRESENT_VOLTAGE)
    if result == 0:
        print(f"当前电压: {voltage/10.0:.1f}V")
        if voltage/10.0 < 11.0:
            print(f"  [警告] 电压偏低")
    
    # 读取温度
    temp, result, error = packet_handler.read1ByteTxRx(port_handler, servo_id, ADDR_PRESENT_TEMPERATURE)
    if result == 0:
        print(f"当前温度: {temp}°C")
        if temp > 70:
            print(f"  [警告] 温度过高")
    
    # 读取移动状态
    moving, result, error = packet_handler.read1ByteTxRx(port_handler, servo_id, ADDR_MOVING_STATUS)
    if result == 0:
        print(f"移动状态: {moving}")
    
    # 读取错误状态（如果支持）
    try:
        err_status, result, error = packet_handler.read1ByteTxRx(port_handler, servo_id, ADDR_ERROR_STATUS)
        if result == 0:
            print(f"错误状态寄存器: {err_status}")
            if err_status != 0:
                # 解析错误位
                errors = []
                if err_status & 0x01: errors.append("输入电压错误")
                if err_status & 0x02: errors.append("角度限制错误")
                if err_status & 0x04: errors.append("过热错误")
                if err_status & 0x08: errors.append("传感器范围错误")
                if err_status & 0x10: errors.append("电量过低关机")
                if err_status & 0x20: errors.append("指令错误")
                if err_status & 0x40: errors.append("过载错误")
                if errors:
                    print(f"  [严重警告] 检测到错误: {', '.join(errors)}")
    except:
        pass

port_handler.closePort()

print("\n" + "=" * 60)
print("检查完成")
print("=" * 60)