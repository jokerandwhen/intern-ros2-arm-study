import launch
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess
from ament_index_python.packages import get_package_share_directory
import os
import xacro


def generate_launch_description():
    # Get package directory
    pkg_description = get_package_share_directory('soarm101_description')

    # Process URDF
    urdf_file = os.path.join(pkg_description, 'urdf', 'soarm101.urdf.xacro')
    robot_description = xacro.process_file(urdf_file).toxml()

    # RViz config file
    rviz_config_file = os.path.join(pkg_description, 'config', 'view_robot.rviz')

    return LaunchDescription([
        # Robot State Publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': robot_description}]
        ),

        # Joint State Publisher GUI
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen'
        ),

        # RViz
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config_file] if os.path.exists(rviz_config_file) else []
        )
    ])