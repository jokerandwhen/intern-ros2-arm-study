#!/usr/bin/env python3
"""测试使用lerobot的feetech驱动控制joint6"""

import sys
sys.path.insert(0, '/home/ubuntu/.local/lib/python3.10/site-packages')

from lerobot.motors.feetech.feetech import FeetechMotorsBus
from lerobot.motors.feetech.tables import STS_SMS_SERIES_CONFIG
import time

# 初始化
PORT = '/dev/ttyACM0'
BAUDRATE = 1000000

# 配置joint6（gripper）的舵机
motor_config = {
    "gripper": (6, STS_SMS_SERIES_CONFIG),  # (ID, 配置)
}

try:
    # 创建FeetechMotorsBus实例（这是lerobot使用的接口）
    bus = FeetechMotorsBus(
        port=PORT,
        motors=motor_config,
    )
    
    print("="*60)
    print("测试使用lerobot的feetech驱动控制joint6")
    print("="*60)
    
    # 连接
    bus.connect()
    print("✓ 已连接")
    
    # 测试不同角度
    test_angles = [0, 30, 60, 90, 100]
    
    for angle in test_angles:
        print(f"\n设置gripper={angle}°...")
        bus.write("Goal_Position", "gripper", angle)
        
        time.sleep(1.5)
        
        # 读取实际位置
        pos = bus.read("Present_Position", "gripper")
        print(f"  实际位置: gripper={pos:.1f}°")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    
    # 断开连接
    bus.disconnect()
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()