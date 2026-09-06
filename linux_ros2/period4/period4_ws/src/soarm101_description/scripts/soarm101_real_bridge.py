#!/usr/bin/env python3
"""SO-ARM101 实机→虚拟模型同步桥接节点
直接使用 scservo_sdk 读取STS3215舵机数据，发布到/joint_states
可选: 记录数据到CSV用于校准
"""
import csv
import math
import os
from pickle import FALSE
import struct
import time
from datetime import datetime
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


# 实机关节名 → 舵机ID
JOINT_ID_MAP = {
    "shoulder_pan": 1,
    "shoulder_lift": 2,
    "elbow_flex": 3,
    "wrist_flex": 4,
    "wrist_roll": 5,
    "gripper": 6,
}

# 实机关节名 → URDF关节名
JOINT_MAP = {
    "shoulder_pan": "joint1",
    "shoulder_lift": "joint2",
    "elbow_flex": "joint3",
    "wrist_flex": "joint4",
    "wrist_roll": "joint5",
    "gripper": "joint6",
}

# URDF关节顺序
URDF_JOINTS = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6",
               "gripper_right_joint"]

REAL_JOINT_NAMES = list(JOINT_ID_MAP.keys())

# ============================================================
# 零点偏移校准 (舵机度数 → URDF弧度的偏移)
# 舵机中心值 - 这个值对应的URDF角度为0
# 修改方法: 将实机摆到"零位"姿态, 读取舵机角度, 填入下方
# 当前值: 舵机180°中心 → URDF 0° (即 offset = 180°)
# ============================================================
JOINT_ZERO_OFFSET_DEG = {
    "shoulder_pan": 181.8,      # joint1: 水平向前时舵机读数
    "shoulder_lift": 207.9,     # joint2: 水平向前时舵机读数
    "elbow_flex": 356.6,        # joint3: 与link2平行时舵机读数 (等价于 -3.4°)
    "wrist_flex": 178.5,       # joint4: 重新校准零点
    "wrist_roll": 177.3,       # joint5: 水平向前时舵机读数
    "gripper": 80.0,           # joint6: 舵机80°为闭合零位 → URDF 0.014m
}

# 关节方向反转 (True=反转, False=正常)
# 如果实机运动方向与模型相反, 改为 True
JOINT_DIRECTION_INVERT = {
    "shoulder_pan": True,
    "shoulder_lift": True,
    "elbow_flex": True,
    "wrist_flex": True,
    "wrist_roll": True,
    "gripper": False,
}

# 夹爪转换: 实机 0°(闭合)~100°(张开) → URDF 0.014m(闭合)~0m(张开)
GRIPPER_DEG_TO_M = 0.014 / 100.0

# STS3215 控制表地址
ADDR_PRESENT_POSITION = 56  # 当前位置 (2 bytes, 0-4095)
ADDR_PRESENT_SPEED = 58     # 当前速度
ADDR_PRESENT_LOAD = 60      # 当前负载

# 协议常量
SCS_READ = 0x02
SCS_PING = 0x01
INST_READ = 0x02


def read_position(port_handler, packet_handler, motor_id):
    """读取单个舵机当前位置（°）"""
    pos, result, error = packet_handler.read2ByteTxRx(port_handler, motor_id, ADDR_PRESENT_POSITION)
    if result != 0 or error != 0:
        return None
    return pos * 360.0 / 4096.0


def read_all_positions(port_handler, packet_handler, joint_ids):
    """批量读取所有舵机位置"""
    result = {}
    for name, motor_id in joint_ids.items():
        pos = read_position(port_handler, packet_handler, motor_id)
        if pos is not None:
            result[name] = pos
        else:
            result[name] = 0.0
    return result


class RealRobotBridge(Node):
    def __init__(self):
        super().__init__('soarm101_real_bridge')

        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('rate', 30.0)
        self.declare_parameter('record_csv', '')
        port = self.get_parameter('port').value
        rate = self.get_parameter('rate').value
        record_csv = self.get_parameter('record_csv').value

        self.pub = self.create_publisher(JointState, '/joint_states', 10)

        # 尝试连接实机
        self.port_handler = None
        self.packet_handler = None
        self.real_mode = False
        try:
            import scservo_sdk as scs

            self.get_logger().info(f'正在连接实机 {port} ...')
            self.port_handler = scs.PortHandler(port)
            self.packet_handler = scs.PacketHandler(0)  # protocol version 0

            if not self.port_handler.openPort():
                raise RuntimeError(f'无法打开端口 {port}')

            if not self.port_handler.setBaudRate(1000000):
                raise RuntimeError('无法设置波特率')

            self.real_mode = True
            self.get_logger().info(f'✓ 已连接实机: {port}')

            # 读取初始位置
            positions = read_all_positions(
                self.port_handler, self.packet_handler, JOINT_ID_MAP)
            self.get_logger().info(f'初始位置(°): {positions}')

        except Exception as e:
            self.get_logger().error(f'无法连接实机({port}): {type(e).__name__}: {e}')
            self.get_logger().warn('将使用零位作为默认值')

        # CSV 记录
        self.csv_file = None
        self.csv_writer = None
        if record_csv:
            self.csv_file = open(record_csv, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            header = ["timestamp", "elapsed_s"]
            for name in REAL_JOINT_NAMES:
                header.append(f"{name}_deg")
                header.append(f"{name}_rad")
            self.csv_writer.writerow(header)
            self.get_logger().info(f'数据记录: {record_csv}')

        self.start_time = time.time()
        self.count = 0
        self.timer = self.create_timer(1.0 / rate, self.publish_joint_states)

    def publish_joint_states(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = URDF_JOINTS
        elapsed = time.time() - self.start_time

        if self.real_mode and self.port_handler:
            try:
                positions = read_all_positions(
                    self.port_handler, self.packet_handler, JOINT_ID_MAP)

                joint_positions = []
                for real_name in REAL_JOINT_NAMES:
                    deg = positions.get(real_name, 0.0)

                    # 应用零点偏移
                    offset = JOINT_ZERO_OFFSET_DEG.get(real_name, 0.0)
                    calibrated_deg = deg - offset

                    # 应用方向反转
                    if JOINT_DIRECTION_INVERT.get(real_name, False):
                        calibrated_deg = -calibrated_deg

                    if real_name == "gripper":
                        # 夹爪: calibrated_deg=0°(闭合) → 0.014m, -100°(张开) → 0m
                        m = max(0.0, min(0.014, (calibrated_deg + 100.0) * GRIPPER_DEG_TO_M * 0.5))
                        joint_positions.append(m)
                        joint_positions.append(m)
                    else:
                        joint_positions.append(math.radians(calibrated_deg))

                msg.position = joint_positions[:7]
                while len(msg.position) < 7:
                    msg.position.append(0.0)

                # CSV 记录
                if self.csv_writer:
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    row = [ts, f"{elapsed:.3f}"]
                    for name in REAL_JOINT_NAMES:
                        deg = positions.get(name, 0.0)
                        rad = math.radians(deg)
                        row.extend([f"{deg:.2f}", f"{rad:.6f}"])
                    self.csv_writer.writerow(row)
                    self.count += 1
                    if self.count % 300 == 0:
                        self.csv_file.flush()

            except Exception as e:
                self.get_logger().error(f'读取实机失败: {e}')
                msg.position = [0.0] * 7
        else:
            msg.position = [0.0] * 7

        self.pub.publish(msg)

    def destroy_node(self):
        if self.csv_file:
            self.csv_file.close()
            self.get_logger().info(f'CSV已保存: {self.count} 行')
        if self.port_handler:
            try:
                self.port_handler.closePort()
            except Exception:
                pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = RealRobotBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()