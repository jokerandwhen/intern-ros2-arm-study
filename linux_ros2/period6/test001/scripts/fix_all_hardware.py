#!/usr/bin/env python3
"""
舵机硬件全面修复工具
对所有舵机发送RESET命令恢复出厂设置，然后启用扭矩
"""
import time
import scservo_sdk as scs

SERVO_IDS = [1, 2, 3, 4, 5, 6]

def reset_servo(port, servo_id):
    """发送RESET命令(0x06)并清理缓冲区"""
    packet = [0xFF, 0xFF, servo_id, 0x02, 0x06]
    checksum = (~sum(