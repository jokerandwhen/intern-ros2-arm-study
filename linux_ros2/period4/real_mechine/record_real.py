#!/usr/bin/env python3
"""SO-ARM101 实机数据记录器
记录STS3215舵机实际位置、速度、负载，用于校准虚拟模型。

用法:
  # 仅记录数据（不启动ROS2）
  python3 record_real.py --duration 60 --rate 30

  # 同时发布到ROS2 /joint_states 并记录
  python3 record_real.py --ros --duration 300 --rate 30

输出文件: real_mechine/record_YYYYMMDD_HHMMSS.csv
"""
import csv
import math
import os
import sys
import time
import argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 实机关节名（STS3215舵机）
JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex",
               "wrist_flex", "wrist_roll", "gripper"]

# URDF关节名映射
URDF_JOINT_MAP = {
    "shoulder_pan": "joint1",
    "shoulder_lift": "joint2",
    "elbow_flex": "joint3",
    "wrist_flex": "joint4",
    "wrist_roll": "joint5",
    "gripper": "joint6",
}

# 夹爪转换
GRIPPER_DEG_TO_M = 0.014 / 100.0


def connect_robot(port="/dev/ttyACM0"):
    """连接实机"""
    from lerobot.robots.so_follower.so_follower import SOFollower
    from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
    config = SOFollowerRobotConfig(port=port)
    robot = SOFollower(config)
    robot.connect()
    print(f"[OK] 已连接实机: {port}")
    return robot


def read_all(robot):
    """读取所有舵机数据"""
    positions = robot.bus.sync_read("Present_Position")
    velocities = {}
    loads = {}
    for name in JOINT_NAMES:
        try:
            v = robot.bus.read("Present_Speed", name)
            velocities[name] = v
        except Exception:
            velocities[name] = 0.0
        try:
            l = robot.bus.read("Present_Load", name)
            loads[name] = l
        except Exception:
            loads[name] = 0.0
    return positions, velocities, loads


def record_standalone(robot, duration, rate, output_path):
    """纯记录模式（不启动ROS2）"""
    csv_header = ["timestamp", "elapsed_s"]
    for name in JOINT_NAMES:
        csv_header.append(f"{name}_deg")
        csv_header.append(f"{name}_rad")
        csv_header.append(f"{name}_speed")
        csv_header.append(f"{name}_load")

    interval = 1.0 / rate
    start_time = time.time()
    count = 0

    print(f"\n[记录] 开始记录, 时长={duration}s, 频率={rate}Hz")
    print(f"[记录] 输出文件: {output_path}")
    print(f"[记录] 按键 Ctrl+C 可提前停止\n")

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)

        try:
            while time.time() - start_time < duration:
                loop_start = time.time()
                elapsed = loop_start - start_time
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

                positions, velocities, loads = read_all(robot)

                row = [ts, f"{elapsed:.3f}"]
                for name in JOINT_NAMES:
                    deg = positions.get(name, 0.0)
                    rad = math.radians(deg)
                    row.extend([
                        f"{deg:.2f}",
                        f"{rad:.6f}",
                        f"{velocities.get(name, 0.0):.2f}",
                        f"{loads.get(name, 0.0):.2f}",
                    ])

                writer.writerow(row)
                count += 1

                # 进度显示
                if count % rate == 0:
                    remaining = duration - elapsed
                    print(f"  [{elapsed:6.1f}s / {duration}s] 已记录 {count} 行, "
                          f"剩余 {remaining:.0f}s, 关节: {[f'{positions.get(n,0):.1f}°' for n in JOINT_NAMES[:3]]}...")

                # 保持帧率
                sleep_time = interval - (time.time() - loop_start)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print(f"\n[记录] 用户中断, 已记录 {count} 行")

    print(f"\n[完成] 共记录 {count} 行数据")
    print(f"[完成] 文件: {output_path}")
    print(f"[完成] 时长: {elapsed:.1f}s, 平均频率: {count/elapsed:.1f}Hz")


def record_with_ros(robot, duration, rate, output_path):
    """同时发布到ROS2并记录"""
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import JointState

    rclpy.init(args=sys.argv)

    class RecorderNode(Node):
        def __init__(self, robot, duration, rate, output_path):
            super().__init__('real_data_recorder')
            self.robot = robot
            self.rate = rate
            self.duration = duration
            self.start_time = time.time()
            self.count = 0

            self.pub = self.create_publisher(JointState, '/joint_states', 10)
            self.timer = self.create_timer(1.0 / rate, self.callback)

            # CSV
            self.csv_file = open(output_path, 'w', newline='')
            self.writer = csv.writer(self.csv_file)
            header = ["timestamp", "elapsed_s"]
            for name in JOINT_NAMES:
                header.append(f"{name}_deg")
                header.append(f"{name}_rad")
                header.append(f"{name}_speed")
                header.append(f"{name}_load")
            self.writer.writerow(header)

            self.get_logger().info(f'开始记录: {output_path}')

        def callback(self):
            elapsed = time.time() - self.start_time
            if elapsed > self.duration:
                self.get_logger().info(f'记录完成: {self.count} 行')
                self.csv_file.close()
                self.destroy_node()
                rclpy.shutdown()
                return

            positions, velocities, loads = read_all(self.robot)

            # 写入CSV
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            row = [ts, f"{elapsed:.3f}"]
            for name in JOINT_NAMES:
                deg = positions.get(name, 0.0)
                rad = math.radians(deg)
                row.extend([f"{deg:.2f}", f"{rad:.6f}",
                            f"{velocities.get(name, 0.0):.2f}",
                            f"{loads.get(name, 0.0):.2f}"])
            self.writer.writerow(row)
            self.count += 1

            # 发布 /joint_states
            msg = JointState()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.name = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6",
                        "gripper_right_joint"]
            joint_positions = []
            for name in JOINT_NAMES:
                deg = positions.get(name, 0.0)
                if name == "gripper":
                    m = deg * GRIPPER_DEG_TO_M
                    joint_positions.append(m)
                    joint_positions.append(m)
                else:
                    joint_positions.append(math.radians(deg))
            msg.position = joint_positions[:7]
            while len(msg.position) < 7:
                msg.position.append(0.0)
            self.pub.publish(msg)

            if self.count % self.rate == 0:
                self.get_logger().info(
                    f'[{elapsed:.0f}s] {self.count}行, '
                    f'关节: {[f"{positions.get(n,0):.1f}°" for n in JOINT_NAMES[:3]]}...')

    node = RecorderNode(robot, duration, rate, output_path)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser(description='SO-ARM101 实机数据记录器')
    parser.add_argument('--port', default='/dev/ttyACM0', help='串口路径')
    parser.add_argument('--duration', type=float, default=60.0, help='记录时长(秒)')
    parser.add_argument('--rate', type=float, default=30.0, help='记录频率(Hz)')
    parser.add_argument('--ros', action='store_true', help='同时发布到ROS2 /joint_states')
    parser.add_argument('--output', default=None, help='输出文件路径(默认自动生成)')
    args = parser.parse_args()

    if args.output:
        output_path = args.output
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(SCRIPT_DIR, f"record_{ts}.csv")

    print("=" * 60)
    print("SO-ARM101 实机数据记录器")
    print("=" * 60)
    print(f"  串口: {args.port}")
    print(f"  时长: {args.duration}s")
    print(f"  频率: {args.rate}Hz")
    print(f"  ROS2: {'是' if args.ros else '否'}")
    print(f"  输出: {output_path}")
    print("=" * 60)

    robot = connect_robot(args.port)

    try:
        if args.ros:
            record_with_ros(robot, args.duration, args.rate, output_path)
        else:
            record_standalone(robot, args.duration, args.rate, output_path)
    finally:
        try:
            robot.disconnect()
        except Exception:
            pass
        print("[OK] 已断开连接")


if __name__ == "__main__":
    main()