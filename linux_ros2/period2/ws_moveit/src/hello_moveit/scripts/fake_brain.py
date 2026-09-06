#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fake Brain Node - 通过话题发送 JSON 动作指令控制 SOARM101 机械臂

根据 task002.md 接口定义:
- 发布 /brain/action_command (std_msgs/String, JSON 格式)
- 订阅 /brain/action_feedback (std_msgs/String, JSON 格式)

用法:
    ros2 run hello_moveit fake_brain

    或者在终端中手动发布:
    ros2 topic pub /brain/action_command std_msgs/String \
      "{data: '{\"action_type\":\"home\"}'}"
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json


class FakeBrain(Node):
    def __init__(self):
        super().__init__('fake_brain')
        self.command_pub = self.create_publisher(String, '/brain/action_command', 10)
        self.feedback_sub = self.create_subscription(
            String, '/brain/action_feedback', self.feedback_callback, 10)
        self.get_logger().info('Fake Brain started. Ready to receive commands via /brain/action_command')
        self.get_logger().info('Publish JSON commands to /brain/action_command topic')
        self.get_logger().info('')
        self.get_logger().info('Supported commands:')
        self.get_logger().info('  home - Move to home position')
        self.get_logger().info('  move_to - Move to target pose (requires x, y, z, roll, pitch, yaw)')
        self.get_logger().info('  move_joints - Move joints to target angles (requires joint_angles array)')
        self.get_logger().info('  stop - Stop motion')
        self.get_logger().info('')
        self.get_logger().info('Example:')
        self.get_logger().info('  ros2 topic pub /brain/action_command std_msgs/String "{data: \'{\"action_type\":\"home\"}\'}"')

    def feedback_callback(self, msg):
        try:
            data = json.loads(msg.data)
            status = data.get('status', 'unknown')
            action_id = data.get('action_id', 'unknown')
            message = data.get('message', '')
            self.get_logger().info(f'Feedback [{action_id}] {status}: {message}')
        except json.JSONDecodeError:
            self.get_logger().warn(f'Invalid feedback JSON: {msg.data}')

    def send_command(self, command_dict):
        msg = String()
        msg.data = json.dumps(command_dict)
        self.command_pub.publish(msg)
        self.get_logger().info(f'Sent: {msg.data}')


def main(args=None):
    rclpy.init(args=args)
    brain = FakeBrain()
    rclpy.spin(brain)
    brain.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()