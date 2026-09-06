#!/usr/bin/env python3
"""设置机械臂初始位置
用于将虚拟模型和实机同步到初始位置
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import time


class InitialPoseSetter(Node):
    def __init__(self):
        super().__init__('initial_pose_setter')

        # 发布关节状态
        self.joint_pub = self.create_publisher(JointState, '/joint_states', 10)

        # 初始位置（弧度）- 匹配实机初始位置
        self.initial_positions = {
            'joint1': 0.017,      # ~1°
            'joint2': -0.017,     # ~-1°
            'joint3': -3.142,     # ~-180°
            'joint4': -1.112,     # ~-64°
            'joint5': 0.0,        # 0°
            'joint6': 0.0,        # gripper闭合
            'gripper_right_joint': 0.0
        }

        # 关节名称
        self.joint_names = list(self.initial_positions.keys())

        # 定时器：50Hz
        self.timer = self.create_timer(0.02, self.timer_callback)

        self.get_logger().info('初始位置设置节点已启动')
        self.get_logger().info('初始位置: joint1=0.017, joint2=-0.017, joint3=-3.142, joint4=-1.112, joint5=0.0, joint6=0.0')

    def timer_callback(self):
        """定时发布初始位置"""
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = self.joint_names
        msg.position = [self.initial_positions[joint] for joint in self.joint_names]

        self.joint_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = InitialPoseSetter()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()