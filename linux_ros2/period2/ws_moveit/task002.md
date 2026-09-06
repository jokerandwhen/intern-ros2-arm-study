# ROS2 & 机械臂控制 交接文档

## 项目背景

在 RDK S100P（aarch64）上开发一个机器人控制系统，核心是打通 **ROS2 → 机械臂硬件** 的完整链路。

***

## 一、整体架构

```
JSON动作指令                    机械臂物理运动
     │                              │
     ▼                              ▼
┌──────────────────────────────────────────────┐
│               ROS2 通信节点                    │
│  订阅 /brain/action_command（接收JSON指令）     │
│  发布 /brain/action_feedback（返回执行状态）    │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│           MoveIt2 运动规划                     │
│  逆运动学求解 → 避障轨迹规划 → 轨迹输出         │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│        ros2_control 硬件接口插件                │
│  write() → 串口/CAN发指令给电机                │
│  read()  → 读编码器获取关节位置                │
└──────────────┬───────────────────────────────┘
               │
               ▼
          机械臂电机 + 夹爪
```

***

## 二、接口定义

### 2.1 大脑 → ROS（需要订阅的话题）

| 话题名称                    | 类型                | 说明            |
| ----------------------- | ----------------- | ------------- |
| `/brain/action_command` | `std_msgs/String` | 大脑下发的JSON动作指令 |

**指令格式**（JSON字符串）：

```json
// 末端移动到目标位姿
{"action_type":"move_to","target":{"x":0.35,"y":-0.12,"z":0.20,"roll":0.0,"pitch":1.57,"yaw":0.0},"gripper":"open","speed":0.3}

// 关节角度运动
{"action_type":"move_joints","joint_angles":[0.0,-1.57,1.57,0.0,0.0,0.0],"speed":0.2}

// 夹爪控制
{"action_type":"gripper","state":"close"}

// 回零
{"action_type":"home"}

// 急停
{"action_type":"stop"}
```

### 2.2 ROS → 大脑（需要发布的话题）

| 话题名称                     | 类型                       | 说明                 |
| ------------------------ | ------------------------ | ------------------ |
| `/brain/action_feedback` | `std_msgs/String`        | 执行状态反馈             |
| `/joint_states`          | `sensor_msgs/JointState` | 各关节实时位置/速度（ROS2标准） |

**反馈格式**（JSON字符串）：

```json
// 成功
{"status":"success","action_id":"move_001","message":"已到达目标位置"}

// 执行中
{"status":"running","action_id":"move_001","progress":0.6}

// 失败
{"status":"failed","action_id":"move_001","message":"逆解失败，目标不可达"}
```

### 2.3 服务接口（ROS端提供）

| 服务名称              | 类型                 | 说明    |
| ----------------- | ------------------ | ----- |
| `/brain/stop_arm` | `std_srvs/Trigger` | 紧急停止  |
| `/brain/go_home`  | `std_srvs/Trigger` | 机械臂回零 |

***

## 三、需要实现的代码

### 模块1：ROS2通信节点

```python
# ros2/action_bridge.py
# 功能：连接外部系统与ROS2
# - 订阅 /brain/action_command
# - 解析JSON并调用对应MoveIt2接口
# - 发布 /brain/action_feedback
```

### 模块2：MoveIt2规划接口

```python
# ros2/arm_commander.py
# 功能：封装机械臂运动控制API
# 接口：
#   move_to(target_pose) → bool  # 笛卡尔运动
#   move_joints(angles)  → bool  # 关节空间运动
#   gripper(state)       → bool  # 夹爪控制
#   go_home()            → bool  # 回零
#   stop()                       # 急停
```

### 模块3：硬件接口插件

```python
# ros2/hardware_interface.py
# 继承 SystemInterface，实现：
#   read()  → 从串口/CAN读取编码器数据
#   write() → 将目标角度写入电机驱动器
```

### 模块4：控制器配置

```yaml
# ros2/config/controllers.yaml
# 关节轨迹控制器 + 状态广播器 的配置
```

***

## 四、学习资料

### &#x20;侧重"ROS2通信 + MoveIt2运动规划"

| 学习内容                  | 资料                                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------- |
| ROS2节点/话题/服务编程（rclpy） | <https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries.html>                   |
| MoveIt2 Python API    | <https://moveit.picknik.ai/humble/doc/tutorials/quickstart_in_rviz/quickstart_in_rviz.html> |
| MoveJ / MoveL 实践      | MoveIt2官方教程 "Planning with MoveGroup"                                                       |

###  侧重"ros2\_control硬件接口 + 电机驱动"

| 学习内容                    | 资料                                                                          |
| ----------------------- | --------------------------------------------------------------------------- |
| ros2\_control架构         | <https://control.ros.org/master/>                                           |
| 硬件接口插件开发（read/write）    | <https://github.com/ros-controls/ros2_control_demos/tree/humble/example_2>  |
| URDF建模 + ros2\_control块 | <https://docs.ros.org/en/humble/Tutorials/Intermediate/URDF/URDF-Main.html> |
| 串口通信                    | Python pyserial 库                                                           |

***

## 六、启动方式

```bash
# 终端1：启动ROS2 + 硬件驱动
ros2 launch ros2 robot_bringup.launch.py

# 终端2：启动机器人大脑
cd /home/sunrise/voice_assistant
python3 main.py

# 验证：手动发指令看机械臂是否动作
ros2 topic pub /brain/action_command std_msgs/String \
  "{data: '{\"action_type\":\"home\"}'}"
```

***

## 七、关键里程碑

| 目标          | 验证方式                                           |
| ----------- | ---------------------------------------------- |
| ROS2通信节点跑通  | `ros2 topic echo /brain/action_feedback` 能看到返回 |
| 硬件接口打通      | 调用 `write()` 电机能动                              |
| MoveIt2规划跑通 | 发送JSON指令，机械臂按轨迹运动                              |
| 与大脑联调       | 说"把杯子拿给我"，机械臂执行                                |

***

## 八、环境信息

| 项目     | 说明                               |
| ------ | -------------------------------- |
| 硬件平台   | RDK S100P（aarch64）               |
| 操作系统   | Ubuntu 22.04                     |
| ROS版本  | ROS2 Humble                      |
| 机械臂    | （待定，根据实际型号补充）                    |
| 电机通信方式 | 串口 / CAN（待定）                     |
| 项目路径   | `/home/sunrise/voice_assistant/` |

