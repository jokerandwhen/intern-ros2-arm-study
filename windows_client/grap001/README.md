# SoArm101 机械臂抓取控制项目

## 项目概述

本项目用于控制 SoArm101 六轴机械臂（从动臂，COM3）执行抓取任务。支持三种控制方式：键盘控制、固定位置抓取、动作录制与回放。

## 硬件配置

- 机械臂：SoArm101（6轴，STS3215舵机）
- 端口：COM3（USB-Enhanced-SERIAL CH343）
- 波特率：1000000
- 电源：5V（7.4V舵机）

## 文件说明

### 核心文件

| 文件 | 说明 |
|------|------|
| `arm_controller.py` | 机械臂控制器核心类，封装STS3215舵机通信协议 |
| `positions.json` | 固定位置配置文件（记录的关键位置点） |
| `records/` | 录制的动作轨迹存放目录 |

### 控制脚本

| 文件 | 说明 |
|------|------|
| `init_arm.py` | 初始化脚本：连接、检查状态、读取位置 |
| `keyboard_control.py` | 键盘自由控制所有关节 |
| `record_positions.py` | 手动摆位并记录关键位置点 |
| `grasp.py` | 按固定位置序列自动执行抓取 |
| `goto.py` | 移动到指定位置（测试用） |
| `record_replay.py` | 动作录制与回放 |
| `test_connection.py` | 测试控制器连接是否正常 |

---

## 使用方法

### 1. 初始化

```bash
python init_arm.py
```

连接机械臂，检查所有电机状态，读取当前位置，禁用扭矩以便手动移动。

### 2. 键盘控制

```bash
python keyboard_control.py
```

按键说明：

| 按键 | 功能 |
|------|------|
| Q / A | 关节1 (shoulder_pan) 减 / 加 |
| W / S | 关节2 (shoulder_lift) 减 / 加 |
| E / D | 关节3 (elbow_flex) 减 / 加 |
| R / F | 关节4 (wrist_flex) 减 / 加 |
| T / G | 关节5 (wrist_roll) 减 / 加 |
| Y / H | 关节6 (gripper) 减 / 加 |
| O | 完全张开夹爪 |
| C | 闭合夹爪 |
| Z / X | 减小 / 增大步长 |
| 空格 | 读取并显示当前位置 |
| P | 保存当前位置到 positions.json |
| M | 回到初始位置 |
| K | 使能 / 禁用扭矩切换 |
| Ctrl+C | 退出 |

### 3. 固定位置抓取

```bash
python grasp.py
```

按预设序列自动执行7步抓取流程：

```
home → pre_grasp → grasp_close → grasp_up → place → place_release → home
```

当前位置配置（positions.json）：

| 位置 | shoulder_pan | shoulder_lift | elbow_flex | wrist_flex | wrist_roll | gripper | 说明 |
|------|-------------|---------------|------------|------------|------------|---------|------|
| home | 2561 | 426 | 3046 | 1486 | 593 | 1376 | 安全初始位置 |
| pre_grasp | 3671 | 634 | 1138 | 2583 | 518 | 1258 | 物体正上方 |
| grasp_close | 3658 | 379 | 1608 | 1486 | 593 | 1740 | 下降抓取 |
| grasp_up | 3671 | 634 | 1138 | 2583 | 518 | 1740 | 抬起物体 |
| place | 3861 | 503 | 1202 | 2546 | 593 | 1415 | 放置位置 |
| place_release | 3861 | 503 | 1202 | 2546 | 593 | 1258 | 释放物体 |

### 4. 动作录制与回放

#### 录制动作

```bash
python record_replay.py record <任务名>
```

示例：
```bash
python record_replay.py record grasp_demo
```

流程：
1. 程序禁用扭矩，可以手动移动机械臂
2. 按 Enter 开始录制
3. 手动移动机械臂完成抓取动作
4. 按 Esc 停止录制

录制参数：
- 录制频率：20 Hz（每秒20帧）
- 记录内容：6个关节的位置值 + 时间戳
- 保存路径：`records/<任务名>.json`

#### 回放动作（两种方式）

**方式一：逐帧回放**

```bash
python record_replay.py replay <任务名>
```

示例：
```bash
python record_replay.py replay grasp_demo
```

- 按录制的原始帧序列逐帧写入目标位置
- 保持原始时间间隔（20Hz）
- 运动完全复刻录制时的轨迹

**方式二：平滑回放**

```bash
python record_replay.py smooth <任务名>
```

示例：
```bash
python record_replay.py smooth grasp_demo
```

- 在每两帧之间插值3步
- 运动更加流畅顺滑
- 适合对运动平稳性要求高的场景

#### 其他操作

```bash
# 查看已录制的动作
python record_replay.py list

# 删除某个录制
python record_replay.py delete <任务名>
```

#### 录制回放对比

| 特性 | 逐帧回放 (replay) | 平滑回放 (smooth) |
|------|-------------------|-------------------|
| 运动方式 | 逐帧跳转 | 帧间插值 |
| 流畅度 | 还原原始动作 | 更平滑 |
| 速度 | 原速 | 原速 |
| 适用场景 | 精确复刻 | 平稳运动 |

---

## 技术细节

### STS3215 舵机寄存器地址

| 寄存器 | 地址 | 长度 | 说明 |
|--------|------|------|------|
| Torque_Enable | 40 | 1字节 | 扭矩使能（0=禁用，1=使能） |
| Acceleration | 41 | 1字节 | 加速度 |
| Goal_Position | 42 | 2字节 | 目标位置（0-4095） |
| Goal_Speed | 46 | 2字节 | 目标速度 |
| Torque_Limit | 48 | 2字节 | 扭矩限制 |
| Lock | 55 | 1字节 | EEPROM锁（0=解锁，1=锁定） |
| Present_Position | 56 | 2字节 | 当前位置（只读） |
| Present_Voltage | 62 | 1字节 | 当前电压 |
| Present_Temp | 63 | 1字节 | 当前温度 |
| Status | 65 | 1字节 | 状态/错误（只读） |

### 通信协议

- 协议：Feetech SCServo/STS 半双工串行协议
- 数据包格式：`0xFF 0xFF [ID] [Length] [Instruction] [Params...] [Checksum]`
- 指令：0x01=Ping, 0x02=Read, 0x03=Write, 0x83=SyncWrite
- 同步写：可一次写入多个电机的目标位置

### 安全注意事项

1. 运行前确保机械臂活动范围内无障碍物
2. 回放前确认起始位置与录制时接近
3. 紧急情况按 Ctrl+C 停止，程序会自动禁用扭矩
4. 不要同时运行多个控制脚本（会占用同一串口）
5. 退出脚本前确保串口已正确释放
