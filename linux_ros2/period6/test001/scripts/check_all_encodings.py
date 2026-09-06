#!/usr/bin/env python3
"""检查所有舵机的编码模式（通过手动移动测试脉冲范围）"""
import scservo_sdk as scs

PORT = '/dev/ttyACM0'
BAUDRATE = 1000000

JOINT_ID_MAP = {
    "joint1": 1,
    "joint2": 2,
    "joint3": 3,
    "joint4": 4