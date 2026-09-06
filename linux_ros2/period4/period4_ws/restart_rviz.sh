#!/bin/bash
# SO-ARM101 RVIZ 一键重启脚本
# 杀掉所有残留进程，干净启动 display.launch.py
#
# 用法:
#   ./restart_rviz.sh              # 模拟模式 (GUI 手动控制)
#   ./restart_rviz.sh real         # 实机模式 (读取舵机同步)
#   ./restart_rviz.sh real record  # 实机模式 + 记录数据到CSV

set -e

echo "=== 清理残留进程 ==="
pkill -9 -f "ros2 launch" 2>/dev/null || true
pkill -9 -f "robot_state_publisher" 2>/dev/null || true
pkill -9 -f "joint_state_publisher" 2>/dev/null || true
pkill -9 -f "soarm101_real_bridge" 2>/dev/null || true
pkill -9 -f "robot_description_publisher" 2>/dev/null || true
pkill -9 -f rviz2 2>/dev/null || true
sleep 2

echo "=== 重启 ROS2 Daemon ==="
source /opt/ros/humble/setup.bash
ros2 daemon stop 2>/dev/null || true
ros2 daemon start 2>/dev/null
sleep 1

echo "=== 编译 ==="
cd /home/ubuntu/total_internship/period4/period4_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select soarm101_description 2>&1 | tail -5

echo "=== 启动 ==="
source /opt/ros/humble/setup.bash
source install/setup.bash

# Sandbox 限制 .ros/log 写入，改用工作空间内目录
export ROS_LOG_DIR=/home/ubuntu/total_internship/period4/period4_ws/.ros_log
mkdir -p "$ROS_LOG_DIR"

MODE="${1:-sim}"
DO_RECORD="${2:-}"

if [ "$MODE" = "real" ]; then
    echo "模式: 实机同步 (读取 /dev/ttyACM0)"

    # 1. 启动 RVIZ + robot_state_publisher (不启动 bridge，bridge 单独跑)
    echo "启动 RVIZ (无 bridge)..."
    ros2 launch soarm101_description display.launch.py real:=false use_gui:=false &
    LAUNCH_PID=$!
    sleep 3

    # 2. 启动 bridge 脚本（直接运行，绕过 ros2 launch 的 sandbox 限制）
    BRIDGE_SCRIPT="/home/ubuntu/total_internship/period4/period4_ws/install/soarm101_description/lib/soarm101_description/soarm101_real_bridge.py"
    if [ "$DO_RECORD" = "record" ]; then
        RECORD_FILE="/home/ubuntu/total_internship/period4/real_mechine/record_$(date +%Y%m%d_%H%M%S).csv"
        echo "记录: $RECORD_FILE"
        python3 "$BRIDGE_SCRIPT" --ros-args -p port:=/dev/ttyACM0 -p rate:=30.0 \
            -p "record_csv:=$RECORD_FILE" &
        BRIDGE_PID=$!
    else
        python3 "$BRIDGE_SCRIPT" --ros-args -p port:=/dev/ttyACM0 -p rate:=30.0 &
        BRIDGE_PID=$!
    fi

    echo "Bridge PID: $BRIDGE_PID, Launch PID: $LAUNCH_PID"
    echo "按 Ctrl+C 停止所有进程"
    wait $LAUNCH_PID

else
    echo "模式: 模拟 (GUI 手动控制)"
    ros2 launch soarm101_description display.launch.py real:=false
fi