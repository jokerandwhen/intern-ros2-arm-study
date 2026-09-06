import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    declared_arguments = []
    declared_arguments.append(
        DeclareLaunchArgument(
            "rviz_config",
            default_value="",
            description="RViz configuration file (optional)",
        )
    )

    pkg_share = FindPackageShare("soarm101_moveit_config").find("soarm101_moveit_config")
    description_pkg_share = FindPackageShare("soarm101_description").find("soarm101_description")

    urdf_file = os.path.join(description_pkg_share, "urdf", "soarm101.urdf.xacro")
    srdf_file = os.path.join(pkg_share, "config", "soarm101.srdf")
    kinematics_file = os.path.join(pkg_share, "config", "kinematics.yaml")
    ompl_planning_file = os.path.join(pkg_share, "config", "ompl_planning.yaml")
    controllers_file = os.path.join(pkg_share, "config", "controllers.yaml")

    # Load robot description
    robot_description = open(urdf_file).read() if os.path.exists(urdf_file) else ""
    robot_description_semantic = open(srdf_file).read() if os.path.exists(srdf_file) else ""

    # Robot state publisher
    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_description}],
    )

    # MoveGroup
    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            {"robot_description": robot_description},
            {"robot_description_semantic": robot_description_semantic},
            {"robot_description_kinematics": open(kinematics_file).read()} if os.path.exists(kinematics_file) else {},
            open(ompl_planning_file).read() if os.path.exists(ompl_planning_file) else {},
            open(controllers_file).read() if os.path.exists(controllers_file) else {},
        ],
    )

    # RViz
    rviz_config = LaunchConfiguration("rviz_config")
    rviz_arguments = []
    if rviz_config:
        rviz_arguments = ["-d", rviz_config]

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=rviz_arguments,
        parameters=[
            {"robot_description": robot_description},
            {"robot_description_semantic": robot_description_semantic},
            {"robot_description_kinematics": open(kinematics_file).read()} if os.path.exists(kinematics_file) else {},
        ],
    )

    # Static TF (world to base_link)
    static_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_transform_publisher",
        output="log",
        arguments=["0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "world", "base_link"],
    )

    # Joint state publisher GUI
    joint_state_publisher_gui_node = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        name="joint_state_publisher_gui",
        output="screen",
    )

    nodes_to_start = [
        robot_state_publisher_node,
        move_group_node,
        rviz_node,
        static_tf,
        joint_state_publisher_gui_node,
    ]

    return LaunchDescription(declared_arguments + nodes_to_start)