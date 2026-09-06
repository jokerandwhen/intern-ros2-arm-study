#!/usr/bin/env python3
"""发布 robot_description 参数到 /robot_description 话题，供 RVIZ 使用"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class RobotDescriptionPublisher(Node):
    def __init__(self):
        super().__init__('robot_description_publisher')
        self.declare_parameter('robot_description', '')
        desc = self.get_parameter('robot_description').value
        pub = self.create_publisher(
            String,
            '/robot_description',
            qos_profile=rclpy.qos.QoSProfile(
                depth=1,
                durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
            ),
        )
        msg = String()
        msg.data = desc
        pub.publish(msg)
        self.get_logger().info('robot_description published')


def main(args=None):
    rclpy.init(args=args)
    node = RobotDescriptionPublisher()
    rclpy.spin_once(node, timeout_sec=1)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()