"""SO-ARM101 模型显示 Launch 文件
支持两种模式:
  real=true  → 读取实机舵机位置，驱动虚拟模型
  real=false → 使用 joint_state_publisher_gui 手动控制
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_dir = get_package_share_directory('soarm101_description')
    xacro_path = os.path.join(pkg_dir, 'urdf', 'soarm101.xacro')

    robot_description = ParameterValue(
        Command(['xacro ', xacro_path]),
        value_type=str
    )

    use_real = LaunchConfiguration('real')
    use_gui = LaunchConfiguration('use_gui')
    record_csv = LaunchConfiguration('record_csv')

    return LaunchDescription([
        DeclareLaunchArgument(
            'real',
            default_value='false',
            description='true=实机同步模式, false=手动模拟模式'),
        DeclareLaunchArgument(
            'use_gui',
            default_value='true',
            description='是否使用 joint_state_publisher_gui (仅 sim 模式)'),
        DeclareLaunchArgument(
            'record_csv',
            default_value='',
            description='实机模式: CSV文件路径, 记录所有舵机数据'),

        # === 模拟模式: GUI 手动控制 ===
        # 仅当 real=false 且 use_gui=true 时启动
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher',
            output='screen',
            condition=IfCondition(use_gui),
            parameters=[{
                'use_mimic_tag': True,
                'rate': 50,
            }],
        ),

        # === 实机模式: 读取舵机位置 ===
        # 注意: 由于 sandbox 限制，bridge 节点需单独运行（不在 ros2 launch 内）
        # 使用: python3 scripts/soarm101_real_bridge.py --ros-args -p record_csv:=xxx.csv
        Node(
            package='soarm101_description',
            executable='soarm101_real_bridge.py',
            name='real_robot_bridge',
            output='screen',
            condition=IfCondition(use_real),
            parameters=[{
                'rate': 30.0,
                'record_csv': record_csv,
            }],
        ),

        # robot_state_publisher (两种模式都需要)
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[{
                'robot_description': robot_description,
            }],
        ),

        # 发布 /robot_description 话题
        Node(
            package='soarm101_description',
            executable='robot_description_publisher.py',
            name='robot_description_publisher',
            parameters=[{
                'robot_description': robot_description,
            }],
        ),

        # RVIZ (两种模式都需要)
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', os.path.join(pkg_dir, 'urdf', 'soarm101.rviz')],
        ),
    ])