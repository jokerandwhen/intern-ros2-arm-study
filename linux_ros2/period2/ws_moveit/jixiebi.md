# Panda 机械臂 MTC 控制系统 - 运行指南

使用 Panda 机械臂（来自 moveit\_resources\_panda）和 MoveIt Task Constructor。

## 三步启动流程

### 终端1：启动 Panda 环境（MoveIt + RViz + ros2\_control）

```bash
source ~/ws_moveit/install/setup.bash
ros2 launch hello_moveit mtc_demo.launch.py
```

启动内容：

- **Panda 机器人模型**（7自由度机械臂 + 夹爪）
- robot\_state\_publisher
- move\_group（带 ExecuteTaskSolutionCapability）
- rviz2（使用 mtc.rviz 配置）
- ros2\_control\_node（仿真硬件）
- panda\_arm\_controller, panda\_hand\_controller, joint\_state\_broadcaster
- static\_transform\_publisher（world -> panda\_link0）

等待看到 "You can start planning now!" 后继续。

### 终端2：启动 Brain 节点（接收并执行命令）

```bash
source ~/ws_moveit/install/setup.bash
ros2 launch hello_moveit brain.launch.py
```

这个节点会：

- 订阅 `/brain/action_command` 接收 JSON 指令
- 发布 `/brain/action_feedback` 反馈执行状态
- 自动加载 Panda 机器人配置（URDF + SRDF + 运动学 + 控制器）

### 终端3：发送指令

#### 方式 A：使用 fake\_brain 节点（交互式）

```bash
source ~/ws_moveit/install/setup.bash
ros2 run hello_moveit fake_brain.py
```

#### 方式 B：直接发布话题命令

```bash
# 终端3：发送 pick_place 命令
ros2 topic pub /brain/action_command std_msgs/String "{data: '{\"action_type\":\"pick_place\"}'}" --once
# 抓取演示
ros2 topic pub /brain/action_command std_msgs/String "{data: '{\"action_type\":\"pick_place\"}'}" --once

# 回到 home 位置
ros2 topic pub /brain/action_command std_msgs/String "{data: '{\"action_type\":\"home\"}'}" --once
```

## 支持的指令

| action\_type  | 说明         | 附加参数                      |
| ------------- | ---------- | ------------------------- |
| `home`        | 回到 home 位置 | 无                         |
| `move_to`     | 移动到指定位姿    | x, y, z, roll, pitch, yaw |
| `move_joints` | 关节运动       | joint\_angles (数组)        |
| `pick_place`  | 抓取演示（MTC）  | 无                         |
| `stop`        | 停止运动       | 无                         |

## 指令示例

### pick\_place（MTC 抓取演示）

```bash
ros2 topic pub /brain/action_command std_msgs/String "{data: '{\"action_type\":\"pick_place\"}'}" --once
```

### home（回到原点）

```bash
ros2 topic pub /brain/action_command std_msgs/String "{data: '{\"action_type\":\"home\"}'}" --once
```

### move\_to（移动到指定位姿）

```bash
ros2 topic pub /brain/action_command std_msgs/String "{data: '{\"action_type\":\"move_to\",\"x\":0.3,\"y\":0.2,\"z\":0.5,\"roll\":0,\"pitch\":1.57,\"yaw\":0}'}" --once
```

### move\_joints（关节运动）

```bash
ros2 topic pub /brain/action_command std_msgs/String "{data: '{\"action_type\":\"move_joints\",\"joint_angles\":[0.0,-0.785,0.0,-1.571,0.0,0.0,0.0,0.0,0.0]}'}" --once
```

## 停止系统

在每个终端按 `Ctrl+C` 即可停止对应节点。

## 注意事项

1. **必须按顺序启动**：终端1 → 终端2 → 终端3
2. 终端1 必须完全启动后才能启动终端2（否则 brain 节点找不到 robot\_description）
3. 不要单独运行 `ros2 run hello_moveit hello_moveit`，请使用 `ros2 launch hello_moveit brain.launch.py`
4. 机器人模型：Panda（7自由度机械臂 + 2指夹爪）
5. 规划组：`panda_arm`（手臂）和 `hand`（夹爪）
6. 末端坐标系：`panda_link8`

