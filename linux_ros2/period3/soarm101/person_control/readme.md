# SO-ARM100 机械臂控制程序使用指南

## 📋 目录
- [项目简介](#项目简介)
- [快速开始](#快速开始)
- [硬件要求](#硬件要求)
- [软件安装](#软件安装)
- [操作指南](#操作指南)
- [关节参数](#关节参数)
- [常见问题](#常见问题)
- [故障排除](#故障排除)

---

## 项目简介

本项目提供了一个基于 Python 的 SO-ARM100 机械臂控制程序，支持：
- ✅ 实时键盘控制各关节角度
- ✅ 姿态记录与保存（JSON格式）
- ✅ 姿态差异分析
- ✅ 自动归位功能
- ✅ 过载错误清除

---

## 快速开始

### 启动程序

```bash
# 1. 设置串口权限
sudo chmod 666 /dev/ttyACM0

# 2. 运行控制程序
python3 /home/ubuntu/period\ 3/soarm101/person_control/arm_control.py
```

### 基本操作流程

1. **程序启动** → 自动连接机械臂并读取当前位置
2. **选择关节** → 按数字键 1-6 选择要控制的关节
3. **调整角度** → 使用 W/S 键调整角度
4. **保存姿态** → 按 Space 键保存当前姿态
5. **退出程序** → 按 ESC 键退出，自动归位

---

## 硬件要求

### 设备清单
- SO-ARM100 机械臂
- 串口线（USB转串口）
- 电源适配器（6-7.4V）
- 计算机（Linux系统）

### 串口设备
- 默认端口：`/dev/ttyACM0`
- 波特率：自动配置
- 需要读写权限

---

## 软件安装

### 依赖安装

```bash
# 安装 lerobot 库
pip install lerobot --user

# 安装 Feetech 舵机 SDK
pip install feetech-servo-sdk --user
```

### 权限配置

```bash
# 添加用户到 dialout 组
sudo usermod -a -G dialout $USER

# 注销并重新登录使权限生效
# 或者临时设置权限
sudo chmod 666 /dev/ttyACM0
```

---

## 操作指南

### 键盘控制

| 按键 | 功能 | 说明 |
|------|------|------|
| `1-6` | 选择关节 | 按数字键选择对应关节 |
| `W` / `↑` | 增加角度 | 向正方向移动当前关节 |
| `S` / `↓` | 减小角度 | 向负方向移动当前关节 |
| `T` | 设置步长 1° | 精细调整模式 |
| `E` | 设置步长 5° | 默认调整模式 |
| `R` | 设置步长 10° | 快速调整模式 |
| `Space` | 记录姿态 | 保存当前所有关节角度 |
| `L` | 列出姿态 | 显示所有已保存的姿态 |
| `A` | 分析姿态 | 对比相邻姿态的差异 |
| `C` | 清除过载 | 清除舵机过载错误 |
| `Z` | 归位 | 所有关节回安全位置 |
| `H` | 显示帮助 | 显示操作帮助信息 |
| `ESC` / `Q` | 退出程序 | 退出并自动归位 |

### 操作示例

#### 示例1：调整底座角度
```
1. 按 [1] 选择底座关节（shoulder_pan）
2. 按 [W] 向右旋转，按 [S] 向左旋转
3. 按 [T] 切换到 1° 精细调整模式
4. 观察状态栏显示的当前角度
```

#### 示例2：保存多个姿态
```
1. 调整机械臂到目标姿态1
2. 按 [Space] 保存姿态1
3. 调整到姿态2
4. 按 [Space] 保存姿态2
5. 按 [L] 查看所有保存的姿态
6. 按 [A] 分析姿态1到姿态2的变化
```

#### 示例3：清除过载错误
```
1. 当舵机触发过载保护时，界面会显示错误
2. 按 [C] 清除所有舵机的过载状态
3. 等待舵机重新使能
4. 继续正常操作
```

---

## 关节参数

### 关节列表

| ID | 关节名称 | 中文名称 | 角度范围 | 备注 |
|----|---------|---------|----------|------|
| 1 | shoulder_pan | 底座旋转 | -139° ~ 89° | 物理范围限制 |
| 2 | shoulder_lift | 肩部俯仰 | -90° ~ 90° | - |
| 3 | elbow_flex | 肘部弯曲 | -135° ~ 0° | **只能用负数角度** |
| 4 | wrist_flex | 腕部俯仰 | -90° ~ 90° | - |
| 5 | wrist_roll | 腕部旋转 | -180° ~ 180° | - |
| 6 | gripper | 夹爪开合 | 0° ~ 100° | 0=完全闭合，100=完全张开 |

### 归位安全位置

```json
{
  "shoulder_pan": -28.6,
  "shoulder_lift": -48.2,
  "elbow_flex": 0.9,
  "wrist_flex": -1.1,
  "wrist_roll": -5.0,
  "gripper": 42.4
}
```

---

## 常见问题

### Q1: 无法连接机械臂
**现象**：程序提示 `Permission denied: '/dev/ttyACM0'`

**解决方案**：
```bash
# 方案1：临时设置权限
sudo chmod 666 /dev/ttyACM0

# 方案2：永久解决（需要重新登录）
sudo usermod -a -G dialout $USER
```

### Q2: 舵机无响应
**现象**：发送命令后舵机不移动

**排查步骤**：
1. 检查电源是否正常连接
2. 检查串口线是否松动
3. 按 `C` 键清除过载错误
4. 重启程序并重新连接

### Q3: 关节运动范围受限
**现象**：某些关节无法到达理论最大角度

**可能原因**：
- 机械结构限制
- 舵机内部参数限制
- 过载保护触发

**解决方案**：
```bash
# 运行诊断工具
python3 /home/ubuntu/period\ 3/soarm101/fix_joint1_registers.py
```

### Q4: 姿态文件损坏
**现象**：程序无法读取保存的姿态

**解决方案**：
```bash
# 备份并重建姿态文件
cp /home/ubuntu/period\ 3/soarm101/person_control/poses.json poses_backup.json
echo '{"poses": []}' > /home/ubuntu/period\ 3/soarm101/person_control/poses.json
```

---

## 故障排除

### 硬件检查清单

1. **电源检查**
   - 确认电源电压：6-7.4V
   - 检查电源线连接是否牢固
   - 观察电源指示灯状态

2. **机械检查**
   - 手动转动各关节，检查是否有卡死
   - 检查线缆是否缠绕在关节上
   - 观察是否有异常声音

3. **通信检查**
   - 检查 USB 线是否连接
   - 运行 `ls -l /dev/ttyACM*` 确认设备存在
   - 尝试重新插拔 USB 线

### 诊断工具

```bash
# 测试关节1运动范围
python3 /home/ubuntu/period\ 3/soarm101/test_joint1.py

# 清除过载状态
python3 /home/ubuntu/period\ 3/soarm101/clear_overload.py

# 修复关节1寄存器
python3 /home/ubuntu/period\ 3/soarm101/fix_joint1_registers.py
```

---

## 数据文件说明

### poses.json
存储所有保存的姿态数据，格式如下：
```json
{
  "poses": [
    {
      "name": "Pose_1",
      "timestamp": "2026-07-20 12:56:44",
      "angles": {
        "shoulder_pan": -28.56,
        "shoulder_lift": -48.18,
        "elbow_flex": 0.92,
        "wrist_flex": -1.14,
        "wrist_roll": -4.97,
        "gripper": 42.37
      }
    }
  ]
}
```

**注意**：姿态数据只能通过程序添加，无法删除，确保数据安全。

---

## 技术支持

### 项目结构
```
soarm101/
├── person_control/
│   ├── arm_control.py      # 主控制程序
│   ├── poses.json          # 姿态数据文件
│   └── readme.md           # 本文档
├── joint_calibration.csv   # 关节校准数据
├── test_joint1.py          # 关节1测试工具
├── clear_overload.py       # 过载清除工具
└── fix_joint1_registers.py # 寄存器修复工具
```

### 相关资源
- [Lerobot 官方文档](https://github.com/huggingface/lerobot)
- [Feetech 舵机协议](https://www.feetechrc.com/)

---

## 版本历史

- **v1.0** (2026-07-20)
  - 初始版本
  - 支持6关节键盘控制
  - 支持姿态保存与分析
  - 移除删除功能，确保数据安全

---

## 许可证

本项目仅供学习和研究使用。

---

**最后更新**: 2026-07-20
**维护者**: SO-ARM100 项目组