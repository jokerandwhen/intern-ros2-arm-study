# SO-ARM101 Robot Description

ROS2 包：SO-ARM101 机械臂 URDF/Xacro 模型，用于 RVIZ 可视化和仿真。

## 快速启动

### 1. 模拟模式（GUI 手动控制）

```bash
cd /home/ubuntu/total_internship/period4/period4_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch soarm101_description display.launch.py
```

### 2. 实机同步模式

```bash
cd /home/ubuntu/total_internship/period4/period4_ws
bash restart_rviz.sh real
```

### 3. 实机同步 + 数据记录

```bash
cd /home/ubuntu/total_internship/period4/period4_ws
bash restart_rviz.sh real record
```

## 文件结构

```
soarm101_description/
├── urdf/
│   ├── soarm101.xacro      # 机器人模型
│   └── soarm101.rviz       # RVIZ 配置
├── launch/
│   └── display.launch.py   # 启动文件
├── scripts/
│   ├── soarm101_real_bridge.py    # 实机同步节点
│   └── robot_description_publisher.py
└── meshes/                 # 3D 模型文件（如有）
```

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `real` | false | true=实机同步, false=手动模拟 |
| `use_gui` | true | 是否使用滑块控制 |
| `record_csv` | 空 | 实机模式 CSV 记录路径 |