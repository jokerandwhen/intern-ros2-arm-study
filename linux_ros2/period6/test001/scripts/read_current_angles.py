#!/usr/bin/env python3
"""读取实机所有舵机的当前角度"""
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

# 硬件参数
SERVO_PULSE_MAX = 4095
SERVO_FULL_DEG = 360.0

# joint6 特殊参数
JOINT6_PULSE_MIN = 3962
JOINT6_PULSE_MAX = 5474

try:
    port_handler = scs.PortHandler(PORT)
    packet_handler = scs.PacketHandler(0)

    if not port_handler.openPort():
        raise RuntimeError(f'无法打开端口 {PORT}')

    if not port_handler.setBaudRate(BAUDRATE):
        raise RuntimeError('无法设置波特率')

    print(f'正在读取实机当前角度...\n')
    print('='*70)
    print('关节名称         |