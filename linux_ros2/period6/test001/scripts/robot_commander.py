#!/usr/bin/env python3
"""SO-ARM101 实机控制节点
接收GUI/虚拟模型命令，发送到真实机器人
严格隔离虚拟坐标系和硬件物理坐标系
"""
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import time


# 实机关节名 → 舵机ID
JOINT_ID_MAP = {
    "joint1": 1,
    "joint2": 2,
    "joint3": 3,
    "joint4": 4,
    "joint5": 5,
    "joint6": 6,
}

# ==================== 硬件物理坐标系参数（永久固化常量）====================
# 硬件零点偏移：虚拟角度到硬件角度的偏移量
# 计算方式：硬件角度 - 虚拟角度 = 偏移量
# 标定时间：2026-07-24，基于实机当前硬件角度测定
# 虚拟零位：joint1=0°, joint2=0°, joint3=-180°, joint4=-60.9°, joint5=-1.4°, joint6=0°
OFFSET_REAL_ZERO = {
    "joint1": 88.24,      # 硬件88.24° - 虚拟0° = 88.24°
    "joint2": 61.96,      # 硬件61.96° - 虚拟0° = 61.96°
    "joint3": 267.98,     # 硬件87.98° - 虚拟(-180°) = 267.98°
    "joint4": 205.92,     # 硬件145.02° - 虚拟(-60.9°) = 205.92°
    "joint5": 282.03,     # 硬件280.63° - 虚拟(-1.4°) = 282.03°
    # joint6: 重新标定，让虚拟0-90°能正常工作
    # 旧偏移349.01导致虚拟角度超限，改为269°
    # 虚拟0° → 硬件269° → 脉冲3056
    # 虚拟90° → 硬件359° → 脉冲4095
    "joint6": 348.49
}

# 硬件固定参数（不可修改）
SERVO_PULSE_MIN = 0
SERVO_PULSE_MAX = 4095  # 12位标准舵机（单圈0-360°）
SERVO_FULL_DEG = 360.0

# 虚实转向初始配置
DIR_INVERT = {
    "joint1": True,   # 反转：虚拟角度增加 → 硬件角度减少
    "joint2": True,
    "joint3": True,  # 不反转
    "joint4": True,
    "joint5": True,  # 不反转
    "joint6": False  # 不反转
}

# STS3215 控制表地址
ADDR_TORQUE_ENABLE = 40   # 扭矩启用 (1 byte, 0=禁用, 1=启用)
ADDR_GOAL_POSITION = 42   # 目标位置 (2 bytes, 0-4095)
ADDR_PRESENT_POSITION = 56  # 当前位置 (2 bytes)
ADDR_MOVING_ACC = 41      # 加速度 (1 byte, 0-254)


class RobotCommander(Node):
    """实机控制节点"""

    def __init__(self):
        super().__init__('robot_commander')

        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('rate', 30.0)
        port = self.get_parameter('port').value
        rate = self.get_parameter('rate').value

        # 订阅关节命令（来自GUI，纯虚拟坐标系）
        self.joint_sub = self.create_subscription(
            JointState, '/joint_commands',
            self.joint_command_callback, 10
        )

        # 发布实机位置反馈（转换为虚拟坐标系）
        self.real_pub = self.create_publisher(JointState, '/real_robot_joint_states', 10)

        # 实机通信
        self.port_handler = None
        self.packet_handler = None
        self.real_mode = False

        try:
            import scservo_sdk as scs

            self.get_logger().info(f'正在连接实机 {port} ...')
            self.port_handler = scs.PortHandler(port)
            self.packet_handler = scs.PacketHandler(0)

            if not self.port_handler.openPort():
                raise RuntimeError(f'无法打开端口 {port}')

            if not self.port_handler.setBaudRate(1000000):
                raise RuntimeError('无法设置波特率')

            self.real_mode = True
            self.get_logger().info(f'✓ 已连接实机: {port}')

            # 修复所有舵机的角度限制（EPROM，需要先禁用扭矩）
            # 正常舵机模式：单圈0-4095（12位编码）
            self.get_logger().info('正在修复舵机角度限制（0-4095）...')
            try:
                for motor_id in JOINT_ID_MAP.values():
                    # 先禁用扭矩
                    self.packet_handler.write1ByteTxRx(self.port_handler, motor_id, ADDR_TORQUE_ENABLE, 0)
                    time.sleep(0.05)

                    # 读取当前限制
                    min_limit, result, _ = self.packet_handler.read2ByteTxRx(self.port_handler, motor_id, 9)
                    max_limit, result, _ = self.packet_handler.read2ByteTxRx(self.port_handler, motor_id, 11)

                    # 如果角度限制异常，修复为正常值（0-4095）
                    if min_limit != 0 or max_limit != 4095:
                        # Min_Position_Limit (地址9) 和 Max_Position_Limit (地址11)
                        self.packet_handler.write2ByteTxRx(self.port_handler, motor_id, 9, 0)      # 最小0
                        self.packet_handler.write2ByteTxRx(self.port_handler, motor_id, 11, 4095) # 最大4095
                        time.sleep(0.05)

                        self.get_logger().info(f'  舵机{motor_id}: 已修复为 0~4095（原{min_limit}~{max_limit}）')
                    else:
                        self.get_logger().info(f'  舵机{motor_id}: 限制正常（0~4095）')

            except Exception as e:
                self.get_logger().warn(f'  修复失败: {e}')

            # 启用所有舵机扭矩
            self.get_logger().info('正在启用舵机扭矩...')
            for motor_id in JOINT_ID_MAP.values():
                result, error = self.packet_handler.write1ByteTxRx(
                    self.port_handler, motor_id, ADDR_TORQUE_ENABLE, 1
                )
                if result == 0:
                    self.get_logger().info(f'  舵机 {motor_id}: 扭矩已启用')
                else:
                    self.get_logger().warn(f'  舵机 {motor_id}: 扭矩启用失败')
            self.get_logger().info('✓ 所有舵机扭矩已启用')

        except Exception as e:
            self.get_logger().error(f'无法连接实机: {e}')
            self.get_logger().warn('将仅运行虚拟模式（不控制实机）')

        # 最后发送的命令（避免重复发送）
        self.last_positions = {}
        # 轮询读取索引（每次只读一个舵机，避免占用串口）
        self._read_index = 0
        # 缓存上次读取的位置（虚拟坐标系）
        self._cached_positions = {name: 0.0 for name in JOINT_ID_MAP.keys()}

        # 定时器：轮询读取实机位置（10Hz，每次只读1个舵机）
        self.timer = self.create_timer(0.1, self.read_real_positions)

        self.get_logger().info('实机控制节点已启动（虚拟坐标系隔离模式）')

    def joint_command_callback(self, msg):
        """接收关节命令并控制实机"""
        if not self.real_mode:
            return

        try:
            for joint_name, position in zip(msg.name, msg.position):
                if joint_name not in JOINT_ID_MAP:
                    continue

                # 检查是否需要更新（避免重复发送）
                if joint_name in self.last_positions and abs(position - self.last_positions[joint_name]) < 0.001:
                    continue

                self.send_joint_position(joint_name, position)
                self.last_positions[joint_name] = position

        except Exception as e:
            self.get_logger().error(f'发送命令失败: {e}')

    def send_joint_position(self, joint_name, position_rad):
        """
        发送关节位置到实机（虚拟弧度 → 实机脉冲）
        
        所有舵机统一使用12位编码（0-4095，单圈360°）
        
        执行顺序：
        1. 虚拟弧度转为虚拟角度
        2. 根据DIR_INVERT修正转动方向
        3. 叠加OFFSET_REAL_ZERO硬件零点偏移，得到实机目标硬件角度
        4. 换算为0~4095舵机脉冲，做上下限裁剪
        5. 下发脉冲到舵机
        
        输入：虚拟模型弧度（来自GUI）
        """
        # 所有关节统一处理：虚拟弧度 → 实机脉冲
        virtual_deg = math.degrees(position_rad)

        # 根据DIR_INVERT修正转动方向
        if DIR_INVERT[joint_name]:
            virtual_deg = -virtual_deg

        # 叠加OFFSET_REAL_ZERO硬件零点偏移，得到实机目标硬件角度
        servo_deg = virtual_deg + OFFSET_REAL_ZERO[joint_name]

        # 换算为0~4095舵机脉冲，做上下限裁剪
        servo_value = int(servo_deg / SERVO_FULL_DEG * (SERVO_PULSE_MAX + 1))
        servo_value = max(SERVO_PULSE_MIN, min(SERVO_PULSE_MAX, servo_value))
        
        # 6. 下发脉冲到舵机
        motor_id = JOINT_ID_MAP[joint_name]
        result, error = self.packet_handler.write2ByteTxRx(
            self.port_handler, motor_id, ADDR_GOAL_POSITION, servo_value
        )

        if result != 0:
            import scservo_sdk as scs
            err_name = {scs.COMM_PORT_BUSY:'PORT_BUSY', scs.COMM_RX_TIMEOUT:'RX_TIMEOUT',
                        scs.COMM_RX_CORRUPT:'RX_CORRUPT', scs.COMM_TX_ERROR:'TX_ERROR',
                        scs.COMM_RX_FAIL:'RX_FAIL', scs.COMM_TX_FAIL:'TX_FAIL'}.get(result, f'UNKNOWN({result})')
            self.get_logger().warn(
                f'舵机{motor_id}写入失败: result={err_name}, error={error}, '
                f'virtual_deg={virtual_deg:.1f}°, servo_deg={servo_deg:.1f}°, pulse={servo_value}')

    def read_real_positions(self):
        """
        轮询读取实机位置（实机脉冲 → 虚拟弧度）
        
        执行顺序：
        1. 读取舵机原始脉冲值
        2. 脉冲换算为实机硬件原始总角度
        3. 减去OFFSET_REAL_ZERO预存的硬件偏移，剥离实机固有偏差
        4. 根据DIR_INVERT还原虚拟方向
        5. 转为ROS标准虚拟弧度存入缓存
        6. 发布 /real_robot_joint_states 话题
        """
        if not self.real_mode:
            return

        try:
            joint_names = list(JOINT_ID_MAP.keys())
            joint_name = joint_names[self._read_index]
            motor_id = JOINT_ID_MAP[joint_name]

            # 1. 读取舵机原始脉冲值
            pos, result, error = self.packet_handler.read2ByteTxRx(
                self.port_handler, motor_id, ADDR_PRESENT_POSITION
            )

            if result == 0 and error == 0:
                # 所有关节统一处理：脉冲 → 硬件角度 → 虚拟角度 → 弧度
                # 2. 脉冲换算为实机硬件原始总角度
                hardware_deg = pos * SERVO_FULL_DEG / (SERVO_PULSE_MAX + 1)

                # 3. 减去OFFSET_REAL_ZERO预存的硬件偏移
                virtual_deg = hardware_deg - OFFSET_REAL_ZERO[joint_name]

                # 4. 根据DIR_INVERT还原虚拟方向
                if DIR_INVERT[joint_name]:
                    virtual_deg = -virtual_deg

                # 5. 转为ROS标准虚拟弧度存入缓存
                self._cached_positions[joint_name] = math.radians(virtual_deg)

            # 发布缓存的所有位置（虚拟坐标系）
            msg = JointState()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.name = joint_names
            msg.position = [self._cached_positions.get(n, 0.0) for n in joint_names]
            self.real_pub.publish(msg)

            # 轮询下一个舵机
            self._read_index = (self._read_index + 1) % len(joint_names)

        except Exception as e:
            pass

    def destroy_node(self):
        """清理资源"""
        if self.port_handler and self.real_mode:
            # 禁用所有舵机扭矩
            self.get_logger().info('正在禁用舵机扭矩...')
            for motor_id in JOINT_ID_MAP.values():
                try:
                    self.packet_handler.write1ByteTxRx(
                        self.port_handler, motor_id, ADDR_TORQUE_ENABLE, 0
                    )
                except Exception:
                    pass
            self.get_logger().info('✓ 扭矩已禁用')

            try:
                self.port_handler.closePort()
            except Exception:
                pass
        super().destroy_node()


def main(args=None):
    if not rclpy.ok():
        rclpy.init(args=args)
    node = RobotCommander()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()