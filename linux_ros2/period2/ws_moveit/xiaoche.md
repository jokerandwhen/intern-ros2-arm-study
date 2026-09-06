方式 2: 运行完整仿真(差速车会动)
终端 1 - 启动仿真:
source ~/ws_moveit/install/setup.bash
ros2 launch ros2_control_demo_example_2 diffbot.launch.py



终端 2 - 检查硬件接口:
source ~/ws_moveit/install/setup.bash
ros2 control list_hardware_interfaces




终端 3 - 发送速度指令让小车转圈:
source ~/ws_moveit/install/setup.bash
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/TwistStamped "
  header: auto
  twist:
    linear:
      x: 0.7
      y: 0.0
      z: 0.0
    angular:
      x: 0.0
      y: 0.0
      z: 1.0"



您应该看到橙色方块在 RViz 中转圈。


