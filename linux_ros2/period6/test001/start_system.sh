#!/bin/bash
# SO-ARM101 控制系统启动脚本

echo "========================================="
echo "SO-ARM101 GUI控制系统"
echo "========================================="

# 检查ROS2环境
if [ -z "$ROS_DISTRO" ]; then
    echo "加载ROS2环境..."
    source /opt/ros/humble/setup.bash
fi

# 加载工作空间
WS_PATH="/home/ubuntu/total_internship/period4/period4_ws"
if [ -d "$WS_PATH" ]; then
    echo "加载工作空间: $WS_PATH"
    source "$WS_PATH/install/setup.bash"
fi

# 检查实机端口
if [ -e "/dev/ttyACM0" ]; then
    echo "✓ 检测到实机: /dev/ttyACM0"
    REAL_MODE=true
else
    echo "⚠ 未检测到实机，将仅运行虚拟模式"
    REAL_MODE=false
fi

# 启动函数
start_rviz() {
    echo "启动RVIZ..."
    if [ "$REAL_MODE" = true ]; then
        # 不启动 bridge，由 robot_commander 单独处理串口
        ros2 launch soarm101_description display.launch.py real:=false use_gui:=false &
    else
        ros2 launch soarm101_description display.launch.py use_gui:=false &
    fi
    RVIZ_PID=$!
    echo "RVIZ已启动 (PID: $RVIZ_PID)"
}

start_commander() {
    if [ "$REAL_MODE" = true ]; then
        echo "启动实机控制节点..."
        python3 scripts/robot_commander.py &
        COMMANDER_PID=$!
        echo "实机控制节点已启动 (PID: $COMMANDER_PID)"
    fi
}

start_gui() {
    echo "启动GUI控制器..."
    python3 scripts/gui_controller.py &
    GUI_PID=$!
    echo "GUI控制器已启动 (PID: $GUI_PID)"
}

# 主流程
echo ""
echo "选择启动模式:"
echo "1) 完整系统（RVIZ + GUI + 实机控制）"
echo "2) 仅GUI + RVIZ（不控制实机）"
echo "3) 仅GUI控制器"
echo ""
read -p "请选择 (1-3): " choice

case $choice in
    1)
        start_rviz
        sleep 2
        start_commander
        sleep 1
        start_gui
        ;;
    2)
        REAL_MODE=false
        start_rviz
        sleep 2
        start_gui
        ;;
    3)
        start_gui
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac

echo ""
echo "========================================="
echo "系统已启动！按Ctrl+C停止"
echo "========================================="
echo ""

# 等待进程结束
wait