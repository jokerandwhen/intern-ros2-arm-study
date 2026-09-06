# SO-ARM101 GUI控制系统

## 系统概述

本系统实现了通过GUI界面控制虚拟模型，进而控制真实机器人的完整流程。

**核心功能：**
- GUI滑块控制虚拟模型
- 虚拟模型实时驱动实机运动
- 实机位置实时反馈

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户层                                │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          GUI控制器 (gui_controller.py)               │  │
│  │  - PyQt5界面                                         │  │
│  │  - 滑块/数值输入                                     │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │ 关节命令                                │
│                   ↓                                          │
└───────────────────┼─────────────────────────────────────────┘
                    │
┌───────────────────┼─────────────────────────────────────────┐
│                   │           ROS2通信层                     │
│                   │         /joint_states                   │
│                   ↓                                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        实机控制节点 (robot_commander.py)              │  │
│  │  - 订阅关节命令                                      │  │
│  │  - 坐标转换                                          │  │
│  │  - 发送到舵机                                        │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                          │
│                   ↓                                          │
└───────────────────┼─────────────────────────────────────────┘
                    │ 串口通信
                    │ /dev/ttyACM0
                    ↓
┌───────────────────────────────────────────────────────────┐
│                      硬件层                                 │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        STS3215 舵机阵列 (ID: 1-6)                    │  │
│  │  - 6个关节舵机                                        │  │
│  │  - 位置反馈                                           │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

## 数据流程

### 1. GUI → 虚拟模型

**输入：** 用户在GUI中拖动滑块
**输出：** 发送到 `/joint_states` 话题

```python
# gui_controller.py (第248-251行)
def update_joint_position(self, joint_name, position):
    """更新关节位置"""
    if self.ros_node:
        # 关节1-5: 度数转弧度
        # 关节6: 直接使用米制单位
        self.ros_node.set_joint_position(joint_name, position)
```

### 2. 虚拟模型 → 实机

**输入：** 订阅 `/joint_states` 话题
**处理：** 坐标转换（弧度 → 舵机值）
**输出：** 通过串口发送到舵机

```python
# robot_commander.py (第100-119行)
def joint_command_callback(self, msg):
    """接收关节命令并控制实机"""
    for joint_name, position in zip(msg.name, msg.position):
        if joint_name not in JOINT_ID_MAP:
            continue

        # 检查是否需要更新（避免重复发送）
        if joint_name in self.last_positions:
            if abs(position - self.last_positions[joint_name]) < 0.001:
                continue

        self.send_joint_position(joint_name, position)
```

### 3. 坐标转换详解

#### 关节1-5（旋转关节）

**转换链：** GUI度数 → URDF弧度 → 舵机值

```python
# 第136-145行
# 步骤1: 弧度 → 度数
position_deg = math.degrees(position_rad)

# 步骤2: 应用零点偏移
offset = JOINT_ZERO_OFFSET_DEG[joint_name]  # 如 joint1: 181.8°
servo_deg = position_deg + offset

# 步骤3: 方向反转（如果需要）
if JOINT_DIRECTION_INVERT[joint_name]:
    servo_deg = -servo_deg

# 步骤4: 度数 → 舵机值(0-4095)
servo_value = int(servo_deg / 360.0 * 4096.0)
```

**示例：** joint1 = 30° (GUI)
```
GUI:        30°
URDF弧度:  0.5236 rad
零点偏移:  +181.8° → 211.8°
舵机值:    211.8/360 * 4096 = 2406
```

#### 关节6（夹爪）

**转换链：** GUI米制 → 舵机角度

```python
# 第122-133行
# gripper: 位置(m) → 舵机角度(°)
# 0.014m(闭合) → 0°, 0m(张开) → 100°
position_deg = (0.014 - position_rad) / 0.014 * 100.0

# 应用零点偏移
offset = JOINT_ZERO_OFFSET_DEG[joint6]  # 80.0°
servo_deg = position_deg + offset
```

**示例：** gripper = 0.007m (半开)
```
GUI:        0.007m
舵机角度:  (0.014-0.007)/0.014 * 100 = 50°
零点偏移:  +80.0° → 130°
舵机值:    130/360 * 4096 = 1483
```

### 4. 实机反馈 → GUI（可选）

**流程：** 舵机位置 → ROS话题 → GUI显示

```python
# robot_commander.py (第160-197行)
def read_real_positions(self):
    """读取实机实际位置（反馈）"""
    for joint_name, motor_id in JOINT_ID_MAP.items():
        # 步骤1: 读取舵机值
        pos = read2ByteTxRx(motor_id, ADDR_PRESENT_POSITION)

        # 步骤2: 转换链（反向）
        deg = pos * 360.0 / 4096.0
        calibrated_deg = deg - offset
        rad = math.radians(calibrated_deg)

        # 步骤3: 发布到ROS
        msg.position.append(rad)
    self.real_pub.publish(msg)
```

## 关键配置参数

### 零点偏移 (JOINT_ZERO_OFFSET_DEG)

**位置：** `robot_commander.py` 第23-30行

**作用：** 定义URDF零位对应的舵机角度

**当前值：**
```python
JOINT_ZERO_OFFSET_DEG = {
    "joint1": 181.8,   # 水平向前
    "joint2": 207.9,   # 水平向前
    "joint3": 356.6,   # 与link2平行
    "joint4": 178.5,   # 腕部零点
    "joint5": 177.3,   # 水平向前
    "joint6": 80.0,    # 夹爪闭合
}
```

**调整方法：**
1. 将实机摆到标准零位
2. 读取舵机角度（使用校准工具）
3. 更新对应值
4. 重启系统

### 方向反转 (JOINT_DIRECTION_INVERT)

**位置：** `robot_commander.py` 第33-40行

**作用：** 修正关节运动方向

```python
JOINT_DIRECTION_INVERT = {
    "joint1": True,    # 反转
    "joint2": True,
    "joint3": True,
    "joint4": True,
    "joint5": True,
    "joint6": False,   # 不反转
}
```

**规则：**
- `True`: 实机顺时针 → 模型逆时针
- `False`: 保持方向一致

## 文件说明

```
/home/ubuntu/total_internship/period6/test001/
├── scripts/
│   ├── gui_controller.py        # GUI控制器（PyQt5）
│   └── robot_commander.py       # 实机控制节点（ROS2）
├── start_system.sh              # 启动脚本
└── readme.md                    # 本文档
```

### gui_controller.py

**核心类：**
- `RobotControlNode`: ROS2节点，发布关节状态
- `JointControlWidget`: 单个关节控制组件
- `MainWindow`: 主窗口

**关键方法：**
- `update_joint_position()`: 更新关节位置（第248行）
- `timer_callback()`: 定时发布到ROS（第56行）

### robot_commander.py

**核心类：**
- `RobotCommander`: 实机控制节点

**关键方法：**
- `joint_command_callback()`: 接收GUI命令（第100行）
- `send_joint_position()`: 发送到舵机（第120行）
- `read_real_positions()`: 读取实机反馈（第160行）

## 使用方法

### 方式1：完整系统（推荐）

```bash
cd /home/ubuntu/total_internship/period6/test001
chmod +x start_system.sh
./start_system.sh
# 选择 "1) 完整系统"
```

**启动内容：**
1. RVIZ虚拟模型
2. 实机控制节点
3. GUI控制器

### 方式2：手动分步启动

```bash
# 终端1: RVIZ
cd /home/ubuntu/total_internship/period4/period4_ws
source install/setup.bash
ros2 launch soarm101_description display.launch.py use_gui:=false

# 终端2: 实机控制
cd /home/ubuntu/total_internship/period6/test001
python3 scripts/robot_commander.py

# 终端3: GUI
cd /home/ubuntu/total_internship/period6/test001
python3 scripts/gui_controller.py
```

### 方式3：仅虚拟模式（无实机）

```bash
cd /home/ubuntu/total_internship/period6/test001
./start_system.sh
# 选择 "2) 仅GUI + RVIZ"
```

## 常见问题

### 问题1：GUI无法控制实机

**症状：** 滑块动但实机不动

**排查步骤：**
1. 检查实机是否连接：`ls /dev/ttyACM0`
2. 检查robot_commander是否运行：`ps aux | grep robot_commander`
3. 检查ROS话题：`ros2 topic echo /joint_states`

**解决方案：**
```bash
# 重启实机控制节点
python3 scripts/robot_commander.py
```

### 问题2：方向反了

**症状：** GUI向上，实机向下

**解决方案：**
修改 `robot_commander.py` 第33-40行：
```python
JOINT_DIRECTION_INVERT["joint4"] = False  # 改为True或False
```

### 问题3：零位不对

**症状：** GUI显示0°，但实机不在零位

**解决方案：**
1. 手动将实机摆到零位
2. 读取舵机角度（使用校准工具）
3. 更新 `JOINT_ZERO_OFFSET_DEG`

### 问题4：串口权限错误

**错误：** `Permission denied: '/dev/ttyACM0'`

**解决方案：**
```bash
sudo chmod 666 /dev/ttyACM0
```

### 问题5：PyQt5未安装

**错误：** `ModuleNotFoundError: No module named 'PyQt5'`

**解决方案：**
```bash
pip3 install PyQt5
```

## 系统优化

### 避免重复发送

**问题：** GUI持续发送相同命令，导致串口拥塞

**解决：** 在 `robot_commander.py` 中检查位置变化：

```python
# 第111-112行
if abs(position - self.last_positions[joint_name]) < 0.001:
    continue  # 跳过微小变化
```

### 实时反馈显示

**功能：** 在GUI中显示实机实际位置（未来功能）

**实现：**
1. 订阅 `/real_robot_joint_states`
2. 在GUI中更新显示

### 安全限制

**建议：** 添加关节限位检查

```python
# 在 send_joint_position() 中添加
if joint_name != 'joint6':
    if abs(position_rad) > math.pi:  # ±180°
        self.get_logger().warn(f'{joint_name} 超出限位')
        return
```

## 性能参数

- **控制频率：** 30 Hz（GUI发布）
- **串口波特率：** 1000000 bps
- **响应延迟：** <50ms
- **位置精度：** 0.088° (4096分辨率)

## 技术要点总结

1. **坐标转换**：GUI度数 → URDF弧度 → 舵机值
2. **零点偏移**：对齐虚拟模型和实机坐标系
3. **方向反转**：修正关节运动方向差异
4. **话题通信**：`/joint_states` 作为控制桥梁
5. **串口通信**：使用 `scservo_sdk` 控制STS3215舵机

## 更新历史

- **2026-07-22**: 创建完整GUI控制系统
  - 实现GUI → 虚拟模型 → 实机控制链路
  - 添加详细文档说明工作原理