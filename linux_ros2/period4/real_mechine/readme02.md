# SO-ARM101 实机校准与可视化使用指南

## 文件说明

本目录包含实机记录数据和校准工具的相关文件：

- **record\_real.py** - 实机数据记录脚本
- **analyze\_record.py** - 数据分析脚本
- **readme01.md** - 实机记录基础使用说明
- **readme02.md** - 本文件（校准与可视化指南）
- **record\_\*.csv** - 历史记录数据

## 校准流程

### 1. 运行实机同步节点

**作用：** 读取真实机器人舵机位置，发布到 `/joint_states` 话题

```bash
# 终端1：启动实机同步
ccd /home/ubuntu/total_internship/period4/period4_ws
source install/setup.bash
ros2 launch soarm101_description display.launch.py real:=true use_gui:=false
```

**输出示例：**

```
[INFO] [soarm101_real_bridge]: 正在连接实机 /dev/ttyACM0 ...
[INFO] [soarm101_real_bridge]: ✓ 已连接实机: /dev/ttyACM0
[INFO] [soarm101_real_bridge]: 初始位置(°): {'shoulder_pan': 183.6, 'shoulder_lift': 179.9, ...}
```

### 2. 运行校准可视化工具

**作用：** 显示关节状态、末端位姿，帮助诊断虚拟-实机同步问题

```bash
# 终端2：运行可视化
cd /home/ubuntu/total_internship/period4/fixed
source /home/ubuntu/total_internship/period4/period4_ws/install/setup.bash
python3 scripts/calibration_tool.py --visualize
```

**输出内容：**

- **TF 树结构** - 显示各坐标系位置
- **当前关节状态** - 模型角度 vs 实机角度
- **末端执行器坐标** - gripper 的位置和姿态

## 校准参数配置

### 零点偏移 (JOINT\_ZERO\_OFFSET\_DEG)

**文件位置：** `/home/ubuntu/total_internship/period4/period4_ws/src/soarm101_description/scripts/soarm101_real_bridge.py`

**作用：** 定义舵机零位（对应URDF 0°的舵机角度）

**当前配置：**

```python
JOINT_ZERO_OFFSET_DEG = {
    "shoulder_pan": 181.8,      # joint1: 水平向前时舵机读数
    "shoulder_lift": 207.9,     # joint2: 水平向前时舵机读数
    "elbow_flex": 356.6,        # joint3: 与link2平行时舵机读数
    "wrist_flex": 178.5,        # joint4: 腕部零点
    "wrist_roll": 177.3,        # joint5: 水平向前时舵机读数
    "gripper": 80.0,            # joint6: 舵机80°为闭合零位
}
```

**修改方法：**

1. 将实机摆到标准零位姿态
2. 读取舵机角度（从calibration\_tool输出）
3. 更新 `JOINT_ZERO_OFFSET_DEG` 对应值
4. 重启 `soarm101_real_bridge.py`

### 方向反转 (JOINT\_DIRECTION\_INVERT)

**作用：** 修正关节运动方向

**当前配置：**

```python
JOINT_DIRECTION_INVERT = {
    "shoulder_pan": True,
    "shoulder_lift": True,
    "elbow_flex": True,
    "wrist_flex": True,
    "wrist_roll": True,
    "gripper": False,
}
```

**修改规则：**

- `True` = 反转方向（实机顺时针 → 模型逆时针）
- `False` = 保持方向

### URDF 关节轴方向

**文件位置：** `/home/ubuntu/total_internship/period4/period4_ws/src/soarm101_description/urdf/soarm101.xacro`

**关键配置：**

- **joint4 (wrist\_flex):** `<axis xyz="0 1 0"/>` (Y轴)
- **joint6 (gripper):** `<axis xyz="0 1 0"/>` (Y轴平移)

**修改方法：**

1. 如果某个关节方向反了，修改对应的 `<axis>` 值
2. 例如：`xyz="0 -1 0"` 改为 `xyz="0 1 0"`
3. 重新编译：`colcon build --packages-select soarm101_description`

## 常见问题

### 问题1：模型方向与实机相反

**症状：** 实机向上，模型向下

**解决方案：**

```python
# 方法1：修改方向反转标志（soarm101_real_bridge.py）
JOINT_DIRECTION_INVERT["wrist_flex"] = False  # 改为True或False

# 方法2：修改URDF轴方向（soarm101.xacro）
<axis xyz="0 -1 0"/>  # 改为 "0 1 0" 或反之
```

### 问题2：模型穿模/重叠

**原因：** collision geometry 设置过大

**解决方案：**

- 所有 collision 尺寸应比 visual 小（已在URDF中配置）
- 确保每个 `<link>` 都有 `<collision>` 标签

### 问题3：末端位姿无法获取

**错误信息：** `"base_link" passed to lookupTransform argument target_frame does not exist.`

**原因：** 缺少 `robot_state_publisher` 或 TF 数据未发布

**解决方案：**

```bash
# 启动 RVIZ（包含 robot_state_publisher）
cd /home/ubuntu/total_internship/period4/period4_ws
source install/setup.bash
ros2 launch soarm101_description display.launch.py real:=true use_gui:=false
```

### 问题4：关节抖动/不稳定

**原因：** 多个节点同时发布 `/joint_states`

**解决方案：**

- 确保只运行 **一个** joint\_states 发布者
- 不要同时运行 `joint_state_publisher_gui` 和 `soarm101_real_bridge.py`

## 完整操作流程

### 校准流程

1. **启动实机同步**
   ```bash
   ros2 run soarm101_description soarm101_real_bridge.py --ros-args -p port:=/dev/ttyACM0
   ```
2. **检查可视化**
   ```bash
   cd /home/ubuntu/total_internship/period4/fixed
   python3 scripts/calibration_tool.py --visualize
   ```
3. **调整参数**（如果需要）
   - 修改 `soarm101_real_bridge.py` 中的 `JOINT_ZERO_OFFSET_DEG`
   - 或修改 `JOINT_DIRECTION_INVERT`
   - 或修改 URDF 的 `<axis>`
4. **重启验证**
   ```bash
   # 停止进程
   pkill -9 -f soarm101_real_bridge
   # 重启
   ros2 run soarm101_description soarm101_real_bridge.py --ros-args -p port:=/dev/ttyACM0
   ```

### RVIZ可视化流程

```bash
# 启动RVIZ（实机模式）
cd /home/ubuntu/total_internship/period4/period4_ws
source install/setup.bash
ros2 launch soarm101_description display.launch.py real:=true use_gui:=false
```

**注意：** `real:=true` 会自动启动 `soarm101_real_bridge.py`，无需手动运行

### 手动控制流程

```bash
# 启动RVIZ（滑块控制）
ros2 launch soarm101_description display.launch.py

# 或使用命令行控制
python3 scripts/joint_state_publisher.py --joint1 0.5 --joint2 -0.3
```

## 数据记录

### 记录实机数据

```bash
cd /home/ubuntu/total_internship/period4/real_mechine
python3 record_real.py
```

### 分析数据

```bash
python3 analyze_record.py --file record_20260722_124342.csv
```

## 注意事项

1. **端口冲突**：确保 `/dev/ttyACM0` 未被其他程序占用
2. **电源**：实机需要供电才能通信
3. **权限**：首次使用需要添加串口权限：`sudo chmod 666 /dev/ttyACM0`
4. **重启**：修改参数后必须重启节点才能生效
5. **编译**：修改URDF后需要重新编译：`colcon build --packages-select soarm101_description`

## 相关文件

- **URDF模型：** `/home/ubuntu/total_internship/period4/period4_ws/src/soarm101_description/urdf/soarm101.xacro`
- **实机桥接：** `/home/ubuntu/total_internship/period4/period4_ws/src/soarm101_description/scripts/soarm101_real_bridge.py`
- **校准工具：** `/home/ubuntu/total_internship/period4/fixed/scripts/calibration_tool.py`
- **校准数据：** `/home/ubuntu/total_internship/period4/fixed/data/calibration_params_*.yaml`

## 更新历史

- **2026-07-22**: 创建文档，说明校准流程和常见问题

