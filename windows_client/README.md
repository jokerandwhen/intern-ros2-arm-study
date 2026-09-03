# SoArm101 双臂遥操作与视觉抓取系统

> 2026 年 7–8 月实习项目。围绕 SoArm101 六轴机械臂，从零搭建了 **单臂直接控制 → 主从双臂遥操作 → 示教数据采集 → 视觉自动抓取 → VLA 远程推理验证** 的完整链路。
>
> [English version](README_EN.md)

## 项目简介

本项目使用一套 SoArm101 主从臂硬件（共 12 个 STS3215 串行总线舵机），逐步实现了：

1. **底层串口控制**：基于 pyserial 直接实现 Feetech STS3215 半双工协议，读写舵机寄存器，完成关节级控制；
2. **主从遥操作**：人工拖动示教臂，从动臂实时跟随同步，用于示教数据采集；
3. **示教录制与回放**：手动演示动作，程序以 20Hz 录制关节轨迹，支持逐帧/平滑两种回放方式；
4. **视觉自动抓取**：使用从动臂夹爪摄像头，分别基于 OpenCV HSV 颜色检测与 YOLOv8 物体检测实现自动抓取，含像素坐标→关节角度的相机标定与视觉伺服微调；
5. **VLA 远程推理验证**：通过 WebSocket + msgpack 与远程 VLA 服务器通信，发送摄像头图像、接收动作指令，验证端到端推理链路。

## 硬件配置

| 设备 | 说明 |
|------|------|
| 示教臂 / 主臂 (Leader) | COM4，12V 电源，12V 舵机，人工手动拖动 |
| 从动臂 (Follower) | COM3，5V 电源，7.4V 舵机，执行动作 |
| 从动臂摄像头 | USB 摄像头，OpenCV 索引 2（装于夹爪，俯视桌面） |
| 串口芯片 | CH343 USB 转串口，波特率 1000000 |
| 上位机 | Windows 11，Python 3.10，CUDA GPU（YOLO 推理加速） |

> **接线要点**：舵机驱动板上的 2-pin 跳线必须短接（USB 与外部电源共地），否则通信不稳定。
>
> **命名说明**：部分早期脚本（如 `main/sync_and_teleop.py`）中把 COM3 称为"主臂"、COM4 称为"辅助臂"，与本文档角色命名相反。本文档以硬件角色为准：**COM4 = 示教臂（被人拖动），COM3 = 从动臂（跟随执行、装摄像头）**。阅读旧脚本时请注意区分。

## 目录结构

```
soarm101/
├── README.md / README_EN.md          # 项目文档（中/英）
├── calibration_data.json              # 双臂校准数据（关节限位、偏移、home 位置）
├── gripper_calibration.json           # 夹爪开合度映射校准数据
│
├── main/                              # 【主流代码】校准、同步、遥操作、控制
├── data_collection/                   # 【数据采集代码】遥操作采集、摄像头录制、VLA 推理
├── diagnosis/                         # 【诊断代码】串口/电机/夹爪/摄像头故障检测
├── fix/                                # 【修复代码】故障清除、EEPROM 解锁、限位修复
├── tests/                              # 【测试代码】开发过程中的连通性/单元测试
│
├── grap001/                           # 功能模块：单臂直接控制（寄存器级协议）
├── sync/                              # 功能模块：纯 pyserial 双臂同步
├── grasp_vision/                      # 功能模块：OpenCV 颜色视觉抓取
├── opencv/                            # 功能模块：YOLOv8 视觉抓取 + 相机标定
│
├── dataset/                           # 遥操作采集的 episode 数据（JSON）
├── datasets/                          # （备用数据目录）
└── camera_recordings/                 # 从动臂摄像头录制的视频（mp4）
```

> **运行方式重要说明**：所有脚本的数据文件路径均为相对路径（如 `calibration_data.json`、`dataset/`、`camera_recordings/`），**请务必从项目根目录运行脚本**，例如 `python main\sync_and_teleop.py`，而不是进入 `main/` 目录后运行。

## 技术栈

| 技术 | 用途 |
|------|------|
| pyserial | 底层串口通信，直接实现 Feetech STS3215 半双工协议 |
| lerobot SDK (`SOFollower`) | 机械臂高层控制 API（校准、观测、动作下发） |
| OpenCV | 视频采集、HSV 颜色检测、图像显示 |
| ultralytics YOLOv8 | 物体检测（`yolov8n.pt`，torch CUDA 加速） |
| numpy / scipy | 数组运算、映射函数拟合（线性回归/插值） |
| websocket + msgpack | 远程 VLA 服务器通信（图像上传、动作下发） |
| msvcrt | Windows 非阻塞键盘输入 |

环境依赖（`pip install`）：

```
pyserial
numpy
scipy
opencv-python
ultralytics            # YOLOv8（自动依赖 torch，本项目使用 torch 2.5.1+cu121）
lerobot                 # SOFollower SDK（本项目基于其源码使用 so_follower 模块）
```

## 开发历程

项目按时间顺序分为五个阶段，每个阶段的成果相对独立、层层递进。

| 阶段 | 时间 | 内容 | 代码位置 |
|------|------|------|---------|
| 1. 单臂直接控制 | 7 月中旬 | pyserial 从寄存器级实现 STS3215 协议、键盘控制、示教录制回放 | `grap001/` |
| 2. 双臂校准与遥操作 | 7 月底 | lerobot SDK 校准、主从同步、episode 数据采集 | `main/`、`data_collection/` |
| 3. 故障诊断与修复 | 8 月初 | 舵机红灯闪烁/电压异常/EEPROM 锁定排查与修复 | `diagnosis/`、`fix/` |
| 4. 视觉自动抓取 | 8 月上旬 | HSV 颜色检测与 YOLOv8 视觉伺服抓取、相机标定 | `grasp_vision/`、`opencv/` |
| 5. VLA 远程推理验证 | 8 月 | WebSocket + msgpack 与远程 VLA 服务端到端验证 | `data_collection/` |

---

## 代码分类详解

### 一、main/ — 主流代码（19 个脚本）

日常使用的核心功能脚本：校准、双臂同步、遥操作、单臂/夹爪控制、安全工具。

**校准类：**

| 脚本 | 说明 |
|------|------|
| `calibrate_robot.py` | 调用 lerobot CLI 完成单臂（COM3）首次校准 |
| `calibrate_and_sync.py` | 双臂连接 → 校准归位 → 主从实时同步 |
| `calibrate_gripper.py` | 手动记录夹爪 5 档开合度（100%/75%/50%/25%/0%），建立主从夹爪映射 |
| `calibrate_gripper_range.py` | 夹爪量程校准 |
| `calibrate_with_direction_check.py` | 校准时检测两臂各关节运动方向一致性，防止镜像反向 |
| `manual_calibrate.py` | 手动校准 |
| `force_recalibrate.py` / `recalibrate_master.py` | 强制重新校准 |
| `create_calibration_from_session.py` | 从遥操作 session 生成校准数据 |
| `extract_calibration_data.py` | 提取校准数据 |

**同步与遥操作类：**

| 脚本 | 说明 |
|------|------|
| `sync_and_teleop.py` | **推荐入口**：启动时分步同步两臂位置（避免突然大幅运动），再进入遥操作 |
| `sync.py` | 纯 pyserial 实现的主从同步（STS3215 寄存器协议） |
| `smart_mapping.py` | 读取校准数据后用线性回归/插值建立映射，实现非线性补偿同步；亦兼串口检测清理工具 |
| `keyboard_control.py` | 键盘逐关节控制 + OpenCV 可视化窗口 |

**控制与安全类：**

| 脚本 | 说明 |
|------|------|
| `single_arm_control.py` | 单臂控制 |
| `control_gripper.py` | 夹爪独立控制 |
| `ultra_safe.py` | 超安全模式：跳过校准直接连接并发送不动测试动作 |
| `test_torque.py` | 连接两臂后立即禁用扭矩，便于手动摆位 |
| `disable_torque.py` | 禁用扭矩 |

### 二、data_collection/ — 数据采集代码（7 个脚本）

遥操作示教数据采集、摄像头视频录制、VLA 远程推理验证。

| 脚本 | 说明 |
|------|------|
| `teleop_simple.py` | 基础主从遥操作，边操控边记录 episode 数据到 `dataset/` |
| `teleop_data_collection.py` | 遥操作 + 从动臂姿态数据采集 |
| `record_camera.py` | 从动臂摄像头录制（q 停止，输出 mp4 到 `camera_recordings/`） |
| `test101.py` | WebSocket 连接远程 VLA 服务器，发送摄像头图像、接收动作指令（单线程版） |
| `test101_multithread.py` | VLA 推理验证（多线程版） |
| `test_simple.py` | VLA 推理 + 机械臂直接控制（跳过握手初始化的简化版） |
| `test_vla_action.py` | VLA 动作数据格式（msgpack + numpy 序列化）验证 |

### 三、diagnosis/ — 诊断代码（25 个脚本）

故障排查工具：串口检测、电机/舵机扫描、夹爪专项诊断、摄像头检测、状态监控。

| 脚本 | 说明 |
|------|------|
| `check_ports.py` / `check_serial.py` | 串口检测（关节运动前的例行检查） |
| `check_bus_methods.py` | 总线通信方法检测 |
| `check_motors.py` / `check_motors_5v.py` | 电机状态检查（后者针对 5V 从动臂） |
| `check_servos.py` / `scan_servos.py` / `detect_motors.py` | 舵机/电机扫描 |
| `check_gripper_motor.py` / `check_master_gripper.py` | 夹爪电机检测 |
| `diagnose_state.py` / `diagnose_voltage.py` | 状态/电压深度诊断 |
| `diagnose_com4_deep.py` / `diag_com3.py` / `diag_correct.py` | 分端口深度诊断 |
| `diagnose_gripper.py` / `diagnose_gripper_registers.py` | 夹爪专项诊断 |
| `comprehensive_gripper_diagnosis.py` | 夹爪综合诊断 |
| `diagnose_camera.py` / `detect_cameras.py` / `find_camera.py` | 摄像头检测 |
| `full_diagnosis.py` / `safe_diagnose.py` | 全量诊断 / 安全诊断 |
| `monitor_com3.py` | COM3 串口实时监听 |
| `read_raw_gripper.py` | 夹爪原始寄存器读取 |

### 四、fix/ — 修复代码（17 个脚本）

故障修复与恢复工具：清故障锁存、LED 红灯闪烁修复、EEPROM 解锁、电压限值修复。

| 脚本 | 说明 |
|------|------|
| `clear_fault.py` / `clear_faults.py` | 清除故障锁存（地址 48 写 0） |
| `fix_led.py` / `fix_all_led.py` | LED 红灯闪烁修复（`fix_all_led.py` 为最终版，适用两臂所有电机） |
| `fix_com3_correct.py` / `fix_com3_undervolt.py` | 从动臂（COM3）修复 / 欠压修复 |
| `fix_com4.py` / `fix_com4_correct.py` / `fix_com4_final.py` | 示教臂（COM4）修复迭代版本 |
| `fix_both_arms.py` | 双臂同时修复 |
| `fix_voltage_limit.py` / `fix_motor2_voltage.py` | 电压限值修复 |
| `unlock_follower.py` / `unlock_gripper.py` / `unlock_raw.py` / `deep_unlock_follower.py` | EEPROM 解锁系列 |
| `reconfigure_gripper.py` | 夹爪重新配置 |

### 五、tests/ — 测试代码（8 个脚本）

开发过程中的连通性与单元测试。

| 脚本 | 说明 |
|------|------|
| `test_bus.py` | 总线通信测试 |
| `test_camera.py` | 摄像头打开测试 |
| `test_movement.py` | 关节运动测试 |
| `test_write.py` | 寄存器写入测试 |
| `test_raw_registers.py` | 原始寄存器读写测试 |
| `test_follower_range.py` | 从动臂行程范围测试 |
| `safe_test.py` | 安全模式测试 |
| `debug_test.py` | 调试测试 |

### 六、功能模块目录（保持原有结构）

#### grap001/ — 阶段 1：单臂直接控制

不依赖任何 SDK，用 pyserial 从寄存器级实现 STS3215 协议（数据包：`0xFF 0xFF [ID] [Length] [Instruction] [Params...] [Checksum]`）。

- `arm_controller.py`：核心控制器类 `SoArmController`（寄存器读写、同步写、平滑移动）；
- `keyboard_control.py`：键盘逐关节控制；
- `record_positions.py` / `positions.json`：手动摆位记录关键位置点；
- `grasp.py`：按 `home → pre_grasp → grasp_close → grasp_up → place → place_release → home` 七步序列自动抓取；
- `record_replay.py`：20Hz 动作录制，逐帧回放（精确复刻）与平滑回放（帧间插值）；
- `records/`：录制的动作轨迹。

详细文档见 [`grap001/README.md`](grap001/README.md)。

#### sync/ — 阶段 2：纯 pyserial 双臂同步模块

- `sync_controller.py`：同步控制器（offsets 偏移 + scales 比例补偿）；
- `sync_run.py`：主从同步启动脚本。

#### grasp_vision/ — 阶段 4a：OpenCV 颜色视觉抓取

- `arm_controller.py`：lerobot SOFollower 封装（安全限位）；
- `object_detector.py`：HSV 颜色检测（红/蓝/绿/黄 + 轮廓过滤）；
- `grasp_main.py`：视觉抓取主程序（手动/自动模式）。

#### opencv/ — 阶段 4b：YOLOv8 视觉抓取 + 相机标定（最终视觉方案）

- `yolo_detect.py`：YOLOv8n 实时检测（80 类 COCO，GPU 加速）；
- `yolo_grasp.py`：YOLO 视觉伺服抓取（后台线程 + 隔帧推理 + 伺服微调 + 下降抓取）；
- `vision_grasp.py`：HSV 颜色视觉伺服抓取（不依赖 GPU 的对照实现）；
- `calibrate.py`：像素坐标 → 关节角度标定；
- `setup_search.py`：搜索位置标定（生成 `search_poses.json`）；
- `yolov8n.pt`：YOLOv8n 预训练模型。

---

## 快速开始

### 1. 环境安装

```bash
pip install pyserial numpy scipy opencv-python ultralytics lerobot
```

### 2. 典型操作流程

**主从遥操作（示教数据采集）：**

```bash
python diagnosis\check_ports.py       # 1. 检查串口（失败则管理员运行 smart_mapping.py，仍失败重启电脑）
python main\sync_and_teleop.py       # 2. 同步两臂位置后进入遥操作
```

**视觉自动抓取（YOLO 版）：**

```bash
cd opencv
python setup_search.py                # 首次：标定搜索位置（生成 search_poses.json）
python calibrate.py                   # 首次：像素坐标→关节角度标定
python yolo_grasp.py                  # 运行自动抓取
```

**数据采集与 VLA 推理：**

```bash
python data_collection\teleop_data_collection.py   # 遥操作 + episode 采集
python data_collection\record_camera.py            # 摄像头录制
python data_collection\test101.py                   # VLA 远程推理验证
```

**单臂示教录制回放（早期方案）：**

```bash
cd grap001
python record_replay.py record grasp_demo   # 录制
python record_replay.py smooth grasp_demo   # 平滑回放
```

## 硬件排障经验

实习期间大量时间花在舵机故障排查上，以下为沉淀的关键经验。

### STS3215 寄存器映射（实测校正版）

> 注意：本项目使用的 2563 型舵机（型号码 0x0A03）寄存器布局与标准 STS/SCS 文档不同，以下为实测结果：
> 地址 11–14 是**角度限位**的高/低字节，不是电压寄存器。曾误将地址 14 读作 Max_Voltage=15，实际是 Max_Angle=4095 的高字节 0x0F。

| 寄存器 | 地址 | 长度 | 说明 |
|--------|------|------|------|
| Min_Position_Limit | 9–10 | 2 字节 | 最小位置限位 |
| Max_Position_Limit | 11–12 | 2 字节 | 最大位置限位 |
| Max_Temperature_Limit | 13 | 1 字节 | 最高温度（80°C） |
| Max_Voltage_Limit | 14 | 1 字节 | 最高电压（16V） |
| Min_Voltage_Limit | 15 | 1 字节 | 最低电压（5V） |
| Torque_Limit | 16–17 | 2 字节 | 扭矩限制 |
| Torque_Enable | 40 | 1 字节 | 扭矩使能（SRAM，可写） |
| Acceleration | 41 | 1 字节 | 加速度（SRAM，可写） |
| Goal_Position | 42 | 2 字节 | 目标位置（SRAM，可写） |
| 故障状态 | 48 | 1 字节 | 清 0 可清除故障锁存 |
| EEPROM Lock | 55 | 1 字节 | 0=解锁，1=锁定 |
| Present_Position | 56 | 2 字节 | 当前位置（只读） |
| Present_Voltage | 62 | 1 字节 | 当前电压（只读） |
| Present_Temp | 63 | 1 字节 | 当前温度（只读） |
| Status | 65 | 1 字节 | 状态/错误（只读） |

### 红灯闪烁修复流程（最终版，对应 `fix/fix_all_led.py`）

1. 确认电源连接正确（示教臂 12V / 从动臂 5V，驱动板跳线短接共地）；
2. 清除故障锁存：地址 48 写 0；
3. 解锁 EEPROM：地址 55 写 0；
4. 设置角度限位：地址 11 写 0（2 字节），地址 13 写 4095（2 字节）；
5. 重新锁定 EEPROM：地址 55 写 1；
6. 再次清除故障：地址 48 写 0；
7. **断电重启约 10 秒**，使 EEPROM 新值生效。

### 串口故障例行处理顺序

```
python diagnosis\check_ports.py          # 常规检测
# 失败 ↓
python main\smart_mapping.py             # 以管理员身份运行
# 仍失败 ↓
重启电脑                                 # 释放被占用的串口
```

### 其他经验

- **夹爪校准**：运行 `main/calibrate_gripper.py`，依次设置完全打开（100%）→ 75% → 50% → 25% → 完全关闭（0%）五档；
- **关节映射**：shoulder_lift 关节不能做简单值反转，需重新设计映射公式保证两臂运动方向一致；
- **视觉伺服方向**：物体在画面右边（dx>0）→ pan 值增大（机械臂左转，摄像头转向右边）；物体在画面左边（dx<0）→ pan 值减小；
- **角度限幅**：shoulder_lift 限幅 −160°~150°，shoulder_pan 限幅 −40°~170°。

## 安全注意事项

1. **写操作仅允许涉及 SRAM 寄存器（地址 40、41、48、42）**，禁止修改 EEPROM（地址 9–39、55）及任何永久保存的硬件配置，除非明确执行修复流程；
2. 运行前确保机械臂活动范围内无障碍物；
3. 回放/遥操作前确认两臂起始位置接近，避免大幅跳变；
4. 紧急情况 Ctrl+C，脚本会自动禁用扭矩；
5. 同一串口同一时间只能被一个脚本占用；
6. 首次给舵机上电前确认电压档位（示教臂 12V 舵机 / 从动臂 7.4V 舵机），供电错误会触发过压保护红灯。

## 数据产出目录

| 目录 | 内容 |
|------|------|
| `dataset/` | 遥操作采集的 episode 关节数据（JSON） |
| `camera_recordings/` | 从动臂摄像头视频（640×480@30fps，mp4，本地生成，不入库） |
| `grap001/records/` | 单臂示教录制的动作轨迹 |
| `calibration_data.json` | 双臂关节校准数据（含备份） |
| `gripper_calibration.json` | 夹爪开合度映射数据 |
