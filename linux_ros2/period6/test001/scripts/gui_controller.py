#!/usr/bin/env python3
"""SO-ARM101 GUI 控制器
使用PyQt5创建控制界面，同时控制虚拟模型和实机
"""
import sys
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QSlider, QLabel, QPushButton, QGroupBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont


# 关节配置（参考 arm_control.py 的实际范围）
# joint1-5: 度数; joint6(夹爪): 0-90°（闭合到张开）
# 默认值对应实机当前硬件角度测定（标定时间：2026-07-24）
# 注意：joint3（肘关节）物理范围受限，需要实测确认
JOINT_CONFIG = {
    'joint1': {'name': 'Joint1 (Base)', 'min': -90.0, 'max': 90.0, 'default': 0.0},
    'joint2': {'name': 'Joint2 (Shoulder)', 'min': -90.0, 'max': 90.0, 'default': 0.0},
    'joint3': {'name': 'Joint3 (Elbow)', 'min': -360.0, 'max': 360.0, 'default': 180.0},  # 暂时限制范围，避免超限
    'joint4': {'name': 'Joint4 (Wrist Pitch)', 'min': -180.0, 'max': 180.0, 'default': -60.9},
    'joint5': {'name': 'Joint5 (Wrist Roll)', 'min': -180.0, 'max': 180.0, 'default': -1.4},
    'joint6': {'name': 'Joint6 (Gripper)', 'min': 0.0, 'max': 90.0, 'default': 0.0},  # 0-90°（闭合到张开）
}


class RobotControlNode(Node):
    """ROS2节点：发布关节状态"""

    def __init__(self):
        super().__init__('robot_control_node')
        self.joint_pub = self.create_publisher(JointState, '/joint_states', 10)
        self.cmd_pub = self.create_publisher(JointState, '/joint_commands', 10)
        # 初始化为JOINT_CONFIG中定义的默认值（度数转弧度）
        import math
        self.current_positions = {
            name: math.radians(config['default']) 
            for name, config in JOINT_CONFIG.items()
        }

    def publish_joint_states(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        # 只发布 joint1-6，gripper_right_joint 由 URDF mimic joint 自动处理
        msg.name = list(JOINT_CONFIG.keys())
        msg.position = [self.current_positions.get(name, 0.0) for name in msg.name]
        self.joint_pub.publish(msg)
        # 同时发布命令（给实机）
        self.cmd_pub.publish(msg)

    def update_position(self, joint_name, value):
        self.current_positions[joint_name] = value


class JointControlWidget(QWidget):
    """单个关节控制组件"""
    position_changed = pyqtSignal(str, float)

    def __init__(self, joint_name, config, parent=None):
        super().__init__(parent)
        self.joint_name = joint_name
        self.config = config
        self.is_gripper = config.get('is_gripper', False)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        name_label = QLabel(self.config['name'])
        name_label.setMinimumWidth(120)
        layout.addWidget(name_label)

        self.slider = QSlider(Qt.Horizontal)
        # 使用配置文件中的范围（夹爪用1000倍精度）
        scale = 1000 if self.is_gripper else 100
        min_val = int(self.config['min'] * scale)
        max_val = int(self.config['max'] * scale)
        default_val = int(self.config['default'] * scale)

        self.slider.setMinimum(min_val)
        self.slider.setMaximum(max_val)
        self.slider.setValue(default_val)

        self.slider.valueChanged.connect(self.on_slider_changed)
        layout.addWidget(self.slider)

        # 显示默认值（夹爪显示毫米，其他显示度数）
        if self.is_gripper:
            default_display = f"{self.config['default']*1000:.1f}mm"
        else:
            default_display = f"{self.config['default']:.1f}°"
        self.value_label = QLabel(default_display)
        self.value_label.setMinimumWidth(60)
        layout.addWidget(self.value_label)

        self.setLayout(layout)

    def on_slider_changed(self, value):
        scale = 1000 if self.is_gripper else 100
        position = value / scale

        # 显示：夹爪显示毫米，其他显示度数
        if self.is_gripper:
            self.value_label.setText(f"{position*1000:.1f}mm")
        else:
            self.value_label.setText(f"{position:.1f}°")

        self.position_changed.emit(self.joint_name, position)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()

        self.ros_node = None
        self.ros_timer = None

        self.init_ros()
        self.init_ui()
        
        # 确保初始位置立即发布到RVIZ
        self.go_home()

    def init_ros(self):
        """初始化ROS2节点"""
        # 如果 rclpy 已经被 shutdown，重新 init
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass
        rclpy.init()
        self.ros_node = RobotControlNode()

        # 用 QTimer 处理 ROS2 事件
        self.ros_timer = QTimer()
        self.ros_timer.timeout.connect(self.spin_ros)
        self.ros_timer.start(30)

    def spin_ros(self):
        """处理 ROS2 事件"""
        try:
            rclpy.spin_once(self.ros_node, timeout_sec=0.001)
        except Exception:
            pass
        # 发布关节状态
        try:
            self.ros_node.publish_joint_states()
        except Exception:
            pass

    def init_ui(self):
        self.setWindowTitle('SO-ARM101 机器人控制器')
        self.setGeometry(100, 100, 800, 500)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()

        # 标题
        title = QLabel('SO-ARM101 GUI 控制器')
        title.setFont(QFont('Arial', 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # 关节控制组
        joints_group = QGroupBox('关节控制')
        joints_layout = QVBoxLayout()

        self.joint_widgets = {}
        for joint_name, config in JOINT_CONFIG.items():
            widget = JointControlWidget(joint_name, config)
            widget.position_changed.connect(self.on_position_changed)
            self.joint_widgets[joint_name] = widget
            joints_layout.addWidget(widget)

        joints_group.setLayout(joints_layout)
        main_layout.addWidget(joints_group)

        # 控制按钮组
        buttons_group = QGroupBox('控制')
        buttons_layout = QHBoxLayout()

        home_btn = QPushButton('归零')
        home_btn.clicked.connect(self.go_home)
        buttons_layout.addWidget(home_btn)

        buttons_group.setLayout(buttons_layout)
        main_layout.addWidget(buttons_group)

        # 状态显示
        self.status_label = QLabel('状态: 已连接ROS2')
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        central_widget.setLayout(main_layout)

    def on_position_changed(self, joint_name, value):
        if self.ros_node:
            # 所有关节：度数转弧度
            rad_val = math.radians(value)
            self.ros_node.update_position(joint_name, rad_val)

    def go_home(self):
        """将所有关节设置为默认值"""
        for joint_name, widget in self.joint_widgets.items():
            scale = 100  # 所有关节统一用100倍缩放
            default_val = int(JOINT_CONFIG[joint_name]['default'] * scale)
            widget.slider.setValue(default_val)

    def closeEvent(self, event):
        """窗口关闭时不 shutdown rclpy，避免影响其他进程"""
        if self.ros_node:
            try:
                self.ros_node.destroy_node()
            except Exception:
                pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
