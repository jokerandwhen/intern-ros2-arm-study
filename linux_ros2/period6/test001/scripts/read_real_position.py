#!/usr/bin/env python3
"""读取实机当前位置（使用scservo_sdk，不依赖lerobot）"""
import math

# 实机关节名 → 舵机ID
JOINT_ID_MAP = {
    "joint1": 1,
    "joint2": 2,
    "joint3": 3,
    "joint4": 4,
    "joint5": 5,
    "joint6": 6,
}

# STS3215 控制表地址
ADDR_PRESENT_POSITION = 56  # 当前位置 (2 bytes)

# 硬件参数
SERVO_PULSE_MAX = 4095
SERVO_FULL_DEG = 360.0

def read_real_position():
    """读取实机当前位置"""
    try:
        import scservo_sdk as scs

        # 连接串口
        port = '/dev/ttyACM0'
        port_handler = scs.PortHandler(port)
        packet_handler = scs.PacketHandler(0)

        if not port_handler.openPort():
            print(f"[ERROR] 无法打开端口 {port}")
            return None

        if not port_handler.setBaudRate(1000000):
            print("[ERROR] 无法设置波特率")
            return None

        print("\n" + "="*80)
        print("读取实机当前位置（硬件角度）")
        print("="*80)

        positions = {}

        for joint_name, motor_id in JOINT_ID_MAP.items():
            pos, result, error = packet_handler.read2ByteTxRx(
                port_handler, motor_id, ADDR_PRESENT_POSITION
            )

            if result == 0 and error == 0:
                # 脉冲 → 硬件角度
                hardware_deg = pos * SERVO_FULL_DEG / (SERVO_PULSE_MAX + 1)
                positions[joint_name] = hardware_deg
                print(f"  {joint_name} (舵机{motor_id}): {hardware_deg:.2f}° (脉冲: {pos})")
            else:
                print(f"  {joint_name} (舵机{motor_id}): 读取失败 (result={result}, error={error})")

        port_handler.closePort()

        print("="*80)
        print("\n对应的OFFSET_REAL_ZERO配置:")
        print("OFFSET_REAL_ZERO = {")
        for joint_name, angle in positions.items():
            print(f'    "{joint_name}": {angle:.2f},')
        print('}')
        print("="*80)
        print("\n说明:")
        print("1. 上述数值是实机当前硬件角度")
        print("2. 如果GUI当前归零，这就是虚拟零位对应的硬件位置")
        print("3. 将这些数值更新到 robot_commander.py 的 OFFSET_REAL_ZERO")

        return positions

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    read_real_position()