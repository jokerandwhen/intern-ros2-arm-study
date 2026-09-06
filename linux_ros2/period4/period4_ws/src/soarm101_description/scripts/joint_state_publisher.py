#!/usr/bin/env python3
"""SO-ARM101 关节状态发布器
手动发布关节角度到 /joint_states，用于控制虚拟模型。

用法:
  # 发布单次关节位置
  python3 joint_state_publisher.py --joint1 0.5 --joint2 -0.3

  # 持续发布（循环）
  python3 joint_state_publisher.py --loop --rate 30

  # 交互模式（从命令行输入角度）
  python3 joint_state_publisher.py --interactive

  # 设置所有关节为指定位置
  python3 joint_state_publisher.py --all 0.0
"""
import argparse
import math
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


# URDF 关节名
JOINT_NAMES = [
    "joint1", "joint2", "joint3",
    "joint4", "joint5", "joint6",
    "gripper_right_joint"
]

# 关节限位 (rad)
JOINT_LIMITS = {
    "joint1": (-3.14159, 3.14159),
    "joint2": (-3.14159, 3.14159),
    "joint3": (-3.14159, 3.14159),
    "joint4": (-1.5708, 1.5708),
    "joint5": (-3.14159, 3.14159),
    "joint6": (-3.14159, 3.14159),
    "gripper_right_joint": (0.0, 0.014),
}


class JointStatePublisher(Node):
    def __init__(self):
        super().__init__('joint_state_publisher')

        self.declare_parameter('rate', 30.0)
        self.rate = self.get_parameter('rate').value

        self.pub = self.create_publisher(JointState, '/joint_states', 10)

        # 当前关节位置
        self.positions = [0.0] * 7

        self.get_logger().info(f'关节状态发布器已启动 (rate={self.rate}Hz)')
        self.get_logger().info(f'关节: {JOINT_NAMES}')

    def publish(self, positions=None):
        """发布关节状态"""
        if positions:
            self.positions = positions[:7]

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = JOINT_NAMES
        msg.position = self.positions

        self.pub.publish(msg)

    def set_joint(self, name, value):
        """设置单个关节角度"""
        if name not in JOINT_NAMES:
            self.get_logger().error(f'未知关节: {name}')
            return False

        idx = JOINT_NAMES.index(name)

        # 检查限位
        if name in JOINT_LIMITS:
            lo, hi = JOINT_LIMITS[name]
            if value < lo or value > hi:
                self.get_logger().warn(
                    f'{name}={value:.3f} 超出限位 [{lo:.2f}, {hi:.2f}]')
                value = max(lo, min(hi, value))

        self.positions[idx] = value
        return True

    def set_all(self, value):
        """设置所有关节为同一角度"""
        for i, name in enumerate(JOINT_NAMES):
            if name in JOINT_LIMITS:
                lo, hi = JOINT_LIMITS[name]
                self.positions[i] = max(lo, min(hi, value))
            else:
                self.positions[i] = value

    def run_loop(self):
        """持续发布"""
        timer = self.create_timer(1.0 / self.rate, self.publish)

        try:
            rclpy.spin(self)
        except KeyboardInterrupt:
            self.get_logger().info('已停止')


def parse_args():
    parser = argparse.ArgumentParser(description='SO-ARM101 关节状态发布器')
    parser.add_argument('--rate', type=float, default=30.0, help='发布频率(Hz)')

    # 各关节角度参数
    for i in range(1, 7):
        parser.add_argument(f'--joint{i}', type=float, help=f'joint{i}角度(rad)')
    parser.add_argument('--gripper', type=float, help='夹爪开合度(0-0.014m)')

    # 快捷参数
    parser.add_argument('--all', type=float, help='设置所有关节为同一角度')
    parser.add_argument('--zero', action='store_true', help='归零位')
    parser.add_argument('--home', action='store_true', help='归初始位(关节2=-1.57)')

    # 运行模式
    parser.add_argument('--loop', action='store_true', help='持续发布')
    parser.add_argument('--interactive', action='store_true', help='交互模式')

    return parser.parse_args()


def interactive_mode(node):
    """交互模式：从命令行输入角度"""
    print("\n交互模式 - 输入关节角度(rad)，用空格分隔7个值")
    print("示例: 0.5 -0.3 0.0 0.0 0.0 0.0 0.007")
    print("输入 'q' 退出\n")

    node.publish()

    while rclpy.ok():
        try:
            user_input = input("关节角度> ").strip()
            if user_input.lower() == 'q':
                break

            values = [float(x) for x in user_input.split()]
            if len(values) != 7:
                print(f"错误: 需要7个值，得到{len(values)}个")
                continue

            node.positions = values
            node.publish()
            print(f"已发布: {[f'{v:.3f}' for v in values]}")

        except ValueError as e:
            print(f"错误: {e}")
        except KeyboardInterrupt:
            break

    print("\n已退出交互模式")


def main():
    args = parse_args()

    rclpy.init(args=sys.argv)
    node = JointStatePublisher()

    # 设置关节位置
    if args.zero:
        node.set_all(0.0)
        node.get_logger().info('归零位')
    elif args.home:
        node.positions = [0.0, -1.57, 0.0, 0.0, 0.0, 0.0, 0.007]
        node.get_logger().info('归初始位')
    elif args.all is not None:
        node.set_all(args.all)
        node.get_logger().info(f'所有关节 = {args.all}')
    else:
        # 逐个设置
        for i in range(1, 7):
            val = getattr(args, f'joint{i}', None)
            if val is not None:
                node.set_joint(f'joint{i}', val)

        if args.gripper is not None:
            node.set_joint('gripper_right_joint', args.gripper)

    # 运行模式
    if args.interactive:
        interactive_mode(node)
    elif args.loop:
        node.get_logger().info(f'持续发布中 (rate={args.rate}Hz), Ctrl+C 停止')
        node.run_loop()
    else:
        # 单次发布
        node.publish()
        node.get_logger().info(f'已发布: {[f"{v:.3f}" for v in node.positions]}')
        time.sleep(0.1)  # 等待消息发出

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()