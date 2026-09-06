#!/usr/bin/env python3
"""SO-ARM101 模型校准工具
通过实机数据校准虚拟模型，包括：
1. 坐标系可视化
2. 末端执行器坐标计算
3. 关节方向验证
4. 校准参数生成

用法:
  # 校准模式：采集实机数据，生成校准参数
  python3 calibration_tool.py --calibrate

  # 可视化模式：显示坐标系和末端位置
  python3 calibration_tool.py --visualize

  # 验证模式：检查关节方向是否正确
  python3 calibration_tool.py --verify

  # 完整流程
  python3 calibration_tool.py --full
"""
import argparse
import csv
import math
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from tf2_ros import Buffer, TransformListener
from geometry_msgs.msg import TransformStamped


# 关节配置
JOINT_NAMES = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6", "gripper_right_joint"]
REAL_JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]

# 舵机ID映射
JOINT_ID_MAP = {
    "shoulder_pan": 1,
    "shoulder_lift": 2,
    "elbow_flex": 3,
    "wrist_flex": 4,
    "wrist_roll": 5,
    "gripper": 6,
}

# STS3215 控制表地址
ADDR_PRESENT_POSITION = 56


class CalibrationTool(Node):
    """校准工具节点"""

    def __init__(self):
        super().__init__('calibration_tool')

        # 参数
        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('duration', 60.0)
        self.declare_parameter('output_dir',
            '/home/ubuntu/total_internship/period4/fixed/data')

        self.port = self.get_parameter('port').value
        self.duration = self.get_parameter('duration').value
        self.output_dir = self.get_parameter('output_dir').value

        # TF 缓冲区
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # 订阅关节状态
        self.joint_sub = self.create_subscription(
            JointState, '/joint_states', self.joint_callback, 10)
        self.current_joints = {}

        # 实机连接
        self.port_handler = None
        self.packet_handler = None
        self.real_connected = False

        # 校准数据
        self.calibration_data = {
            name: {"min": float('inf'), "max": float('-inf'), "values": []}
            for name in REAL_JOINT_NAMES
        }

        self.get_logger().info('校准工具已启动')

    def joint_callback(self, msg: JointState):
        """关节状态回调"""
        for i, name in enumerate(msg.name):
            if i < len(msg.position):
                self.current_joints[name] = msg.position[i]

    def connect_real(self) -> bool:
        """连接实机"""
        try:
            import scservo_sdk as scs

            self.get_logger().info(f'正在连接实机 {self.port} ...')
            self.port_handler = scs.PortHandler(self.port)
            self.packet_handler = scs.PacketHandler(0)

            if not self.port_handler.openPort():
                raise RuntimeError(f'无法打开端口 {self.port}')

            if not self.port_handler.setBaudRate(1000000):
                raise RuntimeError('无法设置波特率')

            self.real_connected = True
            self.get_logger().info(f'✓ 已连接实机: {self.port}')
            return True

        except Exception as e:
            self.get_logger().error(f'连接实机失败: {e}')
            return False

    def read_real_position(self, joint_name: str) -> float:
        """读取实机关节位置（度）"""
        if not self.real_connected:
            return 0.0

        motor_id = JOINT_ID_MAP.get(joint_name)
        if motor_id is None:
            return 0.0

        try:
            pos, result, error = self.packet_handler.read2ByteTxRx(
                self.port_handler, motor_id, ADDR_PRESENT_POSITION)
            if result != 0 or error != 0:
                return 0.0
            return pos * 360.0 / 4096.0
        except Exception:
            return 0.0

    def read_all_real_positions(self) -> Dict[str, float]:
        """读取所有实机关节位置"""
        return {name: self.read_real_position(name) for name in REAL_JOINT_NAMES}

    def get_end_effector_pose(self) -> Tuple[List[float], List[float]]:
        """获取末端执行器位姿"""
        try:
            # 从 base_link 到 gripper_right 的变换
            transform = self.tf_buffer.lookup_transform(
                'base_link', 'gripper_right', rclpy.time.Time())

            pos = [
                transform.transform.translation.x,
                transform.transform.translation.y,
                transform.transform.translation.z
            ]

            quat = [
                transform.transform.rotation.x,
                transform.transform.rotation.y,
                transform.transform.rotation.z,
                transform.transform.rotation.w
            ]

            return pos, quat

        except Exception as e:
            self.get_logger().warn(f'获取末端位姿失败: {e}')
            return [0, 0, 0], [0, 0, 0, 1]

    def get_all_frames(self) -> List[str]:
        """获取所有坐标系"""
        # SO-ARM101 已知的 frames
        return ['base_link', 'link1', 'link2', 'link3', 'link4', 'link5',
                'gripper_left', 'gripper_right', 'tool0']

    def print_joint_info(self):
        """打印关节信息"""
        print("\n" + "=" * 60)
        print("当前关节状态")
        print("=" * 60)

        # 模型关节（弧度）
        print(f"\n{'关节':<20s} {'模型(rad)':>12s} {'模型(°)':>10s}")
        print("-" * 45)
        for name in JOINT_NAMES:
            rad = self.current_joints.get(name, 0.0)
            deg = math.degrees(rad)
            print(f"{name:<20s} {rad:>12.4f} {deg:>10.1f}")

        # 实机关节（度）
        if self.real_connected:
            real_pos = self.read_all_real_positions()
            print(f"\n{'实机关节':<20s} {'角度(°)':>10s}")
            print("-" * 35)
            for name, deg in real_pos.items():
                print(f"{name:<20s} {deg:>10.1f}")

    def print_end_effector(self):
        """打印末端执行器坐标"""
        pos, quat = self.get_end_effector_pose()

        print("\n" + "=" * 60)
        print("末端执行器坐标 (base_link -> gripper_right)")
        print("=" * 60)
        print(f"\n位置 (m):")
        print(f"  X: {pos[0]:>10.4f}")
        print(f"  Y: {pos[1]:>10.4f}")
        print(f"  Z: {pos[2]:>10.4f}")

        print(f"\n姿态 (四元数):")
        print(f"  x: {quat[0]:>10.4f}")
        print(f"  y: {quat[1]:>10.4f}")
        print(f"  z: {quat[2]:>10.4f}")
        print(f"  w: {quat[3]:>10.4f}")

        # 计算欧拉角
        roll, pitch, yaw = self.quat_to_euler(quat)
        print(f"\n姿态 (欧拉角, °):")
        print(f"  Roll:  {math.degrees(roll):>10.1f}")
        print(f"  Pitch: {math.degrees(pitch):>10.1f}")
        print(f"  Yaw:   {math.degrees(yaw):>10.1f}")

    def quat_to_euler(self, quat: List[float]) -> Tuple[float, float, float]:
        """四元数转欧拉角"""
        x, y, z, w = quat

        # Roll (x-axis rotation)
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = math.atan2(sinr_cosp, cosr_cosp)

        # Pitch (y-axis rotation)
        sinp = 2 * (w * y - z * x)
        sinp = max(-1, min(1, sinp))  # clamp
        pitch = math.asin(sinp)

        # Yaw (z-axis rotation)
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        return roll, pitch, yaw

    def print_frames(self):
        """打印所有坐标系"""
        frames = self.get_all_frames()

        print("\n" + "=" * 60)
        print("机器人坐标系")
        print("=" * 60)
        print("\nTF 树结构:")

        # SO-ARM101 主要坐标系
        main_frames = [
            'base_link', 'link1', 'link2', 'link3',
            'link4', 'link5', 'gripper_left', 'gripper_right'
        ]

        for frame in main_frames:
            if frame in frames:
                try:
                    trans = self.tf_buffer.lookup_transform(
                        'base_link', frame, rclpy.time.Time())
                    pos = trans.transform.translation
                    print(f"  {frame:<20s} "
                          f"({pos.x:.3f}, {pos.y:.3f}, {pos.z:.3f})")
                except Exception:
                    print(f"  {frame:<20s} (无法获取)")

    def verify_joint_directions(self) -> Dict[str, bool]:
        """验证关节方向是否正确"""
        print("\n" + "=" * 60)
        print("关节方向验证")
        print("=" * 60)
        print("\n请按以下步骤操作实机，观察模型是否同步跟随：")

        tests = {
            "joint1 (基座旋转)": {
                "操作": "左右旋转基座",
                "期望": "模型 joint1 同向旋转"
            },
            "joint2 (肩部升降)": {
                "操作": "前后摆动大臂",
                "期望": "模型 joint2 同向运动"
            },
            "joint3 (肘关节)": {
                "操作": "弯曲/伸展小臂",
                "期望": "模型 joint3 同向运动"
            },
            "joint4 (腕部俯仰)": {
                "操作": "上下摆动腕部",
                "期望": "模型 joint4 同向运动"
            },
            "joint5 (腕部旋转)": {
                "操作": "旋转末端",
                "期望": "模型 joint5 同向旋转"
            },
            "joint6 (夹爪)": {
                "操作": "开合夹爪",
                "期望": "模型夹爪同步开合"
            }
        }

        results = {}
        print()
        for joint, info in tests.items():
            print(f"\n{joint}:")
            print(f"  操作: {info['操作']}")
            print(f"  期望: {info['期望']}")
            print(f"  结果: ", end="")

            # 简单判断：读取实机位置变化
            if self.real_connected:
                pos1 = self.read_real_position(joint.split()[0].replace("joint", "joint"))
                time.sleep(0.5)
                pos2 = self.read_real_position(joint.split()[0].replace("joint", "joint"))
                diff = abs(pos2 - pos1)
                if diff > 1.0:
                    print("✓ 检测到运动")
                    results[joint] = True
                else:
                    print("- 等待运动...")
                    results[joint] = False
            else:
                print("(未连接实机)")
                results[joint] = False

        return results

    def collect_calibration_data(self, duration: float = 30.0):
        """采集校准数据"""
        print("\n" + "=" * 60)
        print("校准数据采集")
        print("=" * 60)
        print(f"\n请在 {duration} 秒内操作实机，遍历所有关节的全范围运动")
        print("按 Ctrl+C 提前结束\n")

        if not self.real_connected:
            print("[ERROR] 未连接实机，无法采集数据")
            return

        # 初始化数据结构
        self.calibration_data = {
            name: {"min": float('inf'), "max": float('-inf'), "values": [], "timestamps": []}
            for name in REAL_JOINT_NAMES
        }

        start_time = time.time()
        sample_count = 0

        try:
            while time.time() - start_time < duration:
                positions = self.read_all_real_positions()
                elapsed = time.time() - start_time

                for name, deg in positions.items():
                    self.calibration_data[name]["min"] = min(
                        self.calibration_data[name]["min"], deg)
                    self.calibration_data[name]["max"] = max(
                        self.calibration_data[name]["max"], deg)
                    self.calibration_data[name]["values"].append(deg)
                    self.calibration_data[name]["timestamps"].append(elapsed)

                sample_count += 1

                # 进度显示
                if sample_count % 30 == 0:
                    remaining = duration - elapsed
                    print(f"  [{elapsed:.0f}s / {duration}s] "
                          f"已采集 {sample_count} 样本, 剩余 {remaining:.0f}s")

                time.sleep(0.033)  # ~30Hz

        except KeyboardInterrupt:
            print(f"\n用户中断，已采集 {sample_count} 样本")

        print(f"\n采集完成: {sample_count} 样本")

    def save_calibration_data(self):
        """保存校准数据"""
        os.makedirs(self.output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存原始数据
        csv_path = os.path.join(self.output_dir, f"calibration_raw_{timestamp}.csv")
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            header = ["timestamp", "elapsed_s"]
            for name in REAL_JOINT_NAMES:
                header.append(f"{name}_deg")
            writer.writerow(header)

            # 写入数据
            n_samples = len(self.calibration_data[REAL_JOINT_NAMES[0]]["values"])
            for i in range(n_samples):
                row = [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    f"{self.calibration_data[REAL_JOINT_NAMES[0]]['timestamps'][i]:.3f}"
                ]
                for name in REAL_JOINT_NAMES:
                    row.append(f"{self.calibration_data[name]['values'][i]:.2f}")
                writer.writerow(row)

        print(f"\n原始数据已保存: {csv_path}")

        # 保存校准参数
        params_path = os.path.join(self.output_dir, f"calibration_params_{timestamp}.yaml")
        with open(params_path, 'w') as f:
            f.write("# SO-ARM101 校准参数\n")
            f.write(f"# 生成时间: {datetime.now()}\n\n")
            f.write("joints:\n")

            for name in REAL_JOINT_NAMES:
                data = self.calibration_data[name]
                min_deg = data["min"]
                max_deg = data["max"]
                range_deg = max_deg - min_deg

                f.write(f"  {name}:\n")
                f.write(f"    min_deg: {min_deg:.2f}\n")
                f.write(f"    max_deg: {max_deg:.2f}\n")
                f.write(f"    range_deg: {range_deg:.2f}\n")
                f.write(f"    min_rad: {math.radians(min_deg):.4f}\n")
                f.write(f"    max_rad: {math.radians(max_deg):.4f}\n")
                f.write("\n")

        print(f"校准参数已保存: {params_path}")

        # 生成 URDF 参数
        urdf_path = os.path.join(self.output_dir, f"urdf_limits_{timestamp}.txt")
        with open(urdf_path, 'w') as f:
            f.write("# URDF 关节限位参数 (直接复制到 soarm101.xacro)\n\n")

            joint_map = {
                "shoulder_pan": "joint1",
                "shoulder_lift": "joint2",
                "elbow_flex": "joint3",
                "wrist_flex": "joint4",
                "wrist_roll": "joint5",
                "gripper": "joint6",
            }

            for real_name, urdf_name in joint_map.items():
                data = self.calibration_data[real_name]
                min_rad = math.radians(data["min"])
                max_rad = math.radians(data["max"])

                if real_name == "gripper":
                    # 夹爪：度转米 (0-100° -> 0-0.014m)
                    min_m = data["min"] * 0.014 / 100.0
                    max_m = data["max"] * 0.014 / 100.0
                    f.write(f"<!-- {urdf_name} ({real_name}) -->\n")
                    f.write(f'<limit lower="{min_m:.4f}" upper="{max_m:.4f}" '
                            f'effort="5" velocity="0.05"/>\n\n')
                else:
                    f.write(f"<!-- {urdf_name} ({real_name}) -->\n")
                    f.write(f'<limit lower="{min_rad:.4f}" upper="{max_rad:.4f}" '
                            f'effort="15" velocity="3.14"/>\n\n')

        print(f"URDF 参数已保存: {urdf_path}")

    def disconnect(self):
        """断开连接"""
        if self.port_handler:
            try:
                self.port_handler.closePort()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description='SO-ARM101 模型校准工具')
    parser.add_argument('--calibrate', action='store_true',
                        help='采集校准数据')
    parser.add_argument('--visualize', action='store_true',
                        help='可视化模式：显示坐标系和末端位置')
    parser.add_argument('--verify', action='store_true',
                        help='验证关节方向')
    parser.add_argument('--full', action='store_true',
                        help='完整校准流程')
    parser.add_argument('--port', default='/dev/ttyACM0',
                        help='串口路径')
    parser.add_argument('--duration', type=float, default=30.0,
                        help='采集时长(秒)')
    parser.add_argument('--output-dir',
                        default='/home/ubuntu/total_internship/period4/fixed/data',
                        help='输出目录')

    args = parser.parse_args()

    rclpy.init(args=sys.argv)

    tool = CalibrationTool()

    try:
        # 连接实机
        tool.connect_real()

        # 等待 TF 数据和关节状态（需要 spin 来处理回调）
        print("\n等待 TF 数据...")
        for i in range(15):
            rclpy.spin_once(tool, timeout_sec=1.0)
            if tool.current_joints:
                print(f"  已收到关节状态: {len(tool.current_joints)} 个关节")
        # 额外 spin 多次让 TF buffer 填充
        print("  等待 TF buffer 填充...")
        for _ in range(10):
            rclpy.spin_once(tool, timeout_sec=0.5)

        if args.full:
            # 完整流程
            tool.print_frames()
            tool.print_joint_info()
            tool.print_end_effector()
            tool.verify_joint_directions()
            tool.collect_calibration_data(args.duration)
            tool.save_calibration_data()

        elif args.calibrate:
            tool.collect_calibration_data(args.duration)
            tool.save_calibration_data()

        elif args.visualize:
            tool.print_frames()
            tool.print_joint_info()
            tool.print_end_effector()

        elif args.verify:
            tool.verify_joint_directions()

        else:
            # 默认：显示信息
            tool.print_frames()
            tool.print_joint_info()
            tool.print_end_effector()

    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        tool.disconnect()
        tool.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()