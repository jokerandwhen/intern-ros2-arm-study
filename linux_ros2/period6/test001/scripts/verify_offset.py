#!/usr/bin/env python3
"""验证虚拟零位与实机位置的对应关系"""
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import time

# 硬件参数
OFFSET_REAL_ZERO = {
    "joint1": 0.0,
    "joint2": 0.0,
    "joint3": -180.0,
    "joint4": -60.0,
    "joint5": -1.4,
    "joint6": 0.0
}

class OffsetVerifier(Node):
    def __init__(self):
        super().__init__('offset_verifier')
        
        # 订阅虚拟命令
        self.joint_sub = self.create_subscription(
            JointState, '/joint_commands',
            self.joint_command_callback, 10
        )
        
        # 发布验证结果
        self.verify_pub = self.create_publisher(JointState, '/verify_offset', 10)
        
        self.virtual_positions = {}
        self.get_logger().info('偏移验证节点已启动')
        self.get_logger().info('请在GUI中将所有关节归零（虚拟0°）')
        
        # 定时器：每2秒打印一次状态
        self.timer = self.create_timer(2.0, self.print_status)
    
    def joint_command_callback(self, msg):
        """接收虚拟命令"""
        for name, pos in zip(msg.name, msg.position):
            self.virtual_positions[name] = pos
    
    def print_status(self):
        """打印当前状态"""
        if not self.virtual_positions:
            self.get_logger().info('等待GUI数据...')
            return
        
        print("\n" + "="*80)
        print("虚拟零位验证（GUI全部归零）")
        print("="*80)
        print(f"{'关节':<15} {'虚拟角度(rad)':<15} {'虚拟角度(°)':<15} {'预期硬件角度(°)':<20}")
        print("-"*80)
        
        for name, virtual_rad in self.virtual_positions.items():
            virtual_deg = math.degrees(virtual_rad) if name != 'joint6' else virtual_rad * 1000
            expected_hardware = OFFSET_REAL_ZERO.get(name, 0.0)
            
            if name == 'joint6':
                print(f"{name:<15} {virtual_rad:<15.4f} {virtual_deg:<15.1f}mm {expected_hardware:<20.1f}")
            else:
                print(f"{name:<15} {virtual_rad:<15.4f} {virtual_deg:<15.1f}° {expected_hardware:<20.1f}°")
        
        print("="*80)
        print("\n说明：")
        print("1. 虚拟角度(rad) = GUI发送的弧度值")
        print("2. 预期硬件角度(°) = OFFSET_REAL_ZERO配置的值")
        print("3. 请使用lerobot arm_control.py读取实机当前位置")
        print("4. 对比实机位置与预期硬件角度是否一致")
        print("="*80)

def main(args=None):
    rclpy.init(args=args)
    node = OffsetVerifier()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()