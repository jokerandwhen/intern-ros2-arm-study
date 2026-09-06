# SO-ARM101 模型校准

通过实机数据校准虚拟模型，确保虚实同步。

## 目录结构

```
fixed/
├── scripts/
│   └── calibration_tool.py    # 校准工具
├── config/                    # 校准配置
└── data/                      # 校准数据输出
    ├── calibration_raw_*.csv      # 原始数据
    ├── calibration_params_*.yaml  # 校准参数
    └── urdf_limits_*.txt          # URDF 限位参数
```

## 校准流程

### 前置条件

1. **启动 RVIZ 和实机同步**

```bash
cd /home/ubuntu/total_internship/period4/period4_ws
bash restart_rviz.sh real
```

2. **确认实机连接**

```bash
ls -l /dev/ttyACM0
```

### 步骤 1: 可视化检查

显示坐标系、关节状态、末端执行器坐标：

```bash
cd /home/ubuntu/total_internship/period4/fixed/scripts
python3 calibration_tool.py --visualize
```

输出示例：
```
============================================================
机器人坐标系
============================================================
TF 树结构:
  base_link           (0.000, 0.000, 0.000)
  link1               (0.000, 0.000, 0.072)
  link2               (0.000, 0.000, 0.200)
  ...

============================================================
末端执行器坐标 (base_link -> gripper_right_link)
============================================================
位置 (m):
  X:     0.2500
  Y:     0.0000
  Z:     0.3500
```

### 步骤 2: 验证关节方向

检查模型关节方向是否与实机一致：

```bash
python3 calibration_tool.py --verify
```

按照提示操作实机，观察 RVIZ 中模型是否同步同向运动。

### 步骤 3: 采集校准数据

操作实机遍历所有关节的全范围运动：

```bash
# 采集 60 秒
python3 calibration_tool.py --calibrate --duration 60

# 或使用完整流程
python3 calibration_tool.py --full --duration 60
```

采集过程中，请：
- 遍历每个关节的最小/最大位置
- 缓慢、平滑地运动
- 不要超出物理限位

### 步骤 4: 应用校准参数

校准完成后，查看生成的文件：

```bash
ls -la /home/ubuntu/total_internship/period4/fixed/data/
```

关键文件：
- `urdf_limits_*.txt` - 可直接复制到 `soarm101.xacro` 的关节限位参数

应用步骤：

1. 打开 `urdf_limits_*.txt`
2. 复制 `<limit>` 标签
3. 替换 `soarm101.xacro` 中对应关节的限位

示例：
```xml
<!-- joint1 (shoulder_pan) -->
<limit lower="-2.4435" upper="1.5533" effort="15" velocity="3.14"/>
```

## 使用方法

### 完整校准流程

```bash
cd /home/ubuntu/total_internship/period4/fixed/scripts
python3 calibration_tool.py --full --duration 60
```

### 仅可视化

```bash
python3 calibration_tool.py --visualize
```

### 仅采集数据

```bash
python3 calibration_tool.py --calibrate --duration 30
```

### 仅验证关节方向

```bash
python3 calibration_tool.py --verify
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--calibrate` | - | 采集校准数据 |
| `--visualize` | - | 显示坐标系和末端位置 |
| `--verify` | - | 验证关节方向 |
| `--full` | - | 完整校准流程 |
| `--port` | `/dev/ttyACM0` | 串口路径 |
| `--duration` | 30.0 | 采集时长（秒） |
| `--output-dir` | `data/` | 输出目录 |

## 校准参数说明

### 关节限位 (Joint Limits)

- **lower**: 关节最小角度（弧度）
- **upper**: 关节最大角度（弧度）
- **effort**: 最大力矩（Nm）
- **velocity**: 最大速度（rad/s）

### 零点偏移 (Zero Offset)

如果实机零位与模型不一致，需要在 bridge 脚本中添加偏移：

```python
# 示例：joint1 零点偏移 +180°
offset_deg = 180.0
urdf_rad = math.radians(real_deg - offset_deg)
```

## 常见问题

### Q: 模型方向与实机相反？

检查 `soarm101.xacro` 中关节的 `axis` 方向：

```xml
<!-- 正确：Y轴向上 -->
<axis xyz="0 1 0"/>

<!-- 如果方向相反，改为 -->
<axis xyz="0 -1 0"/>
```

### Q: 关节超出限位？

扩大 URDF 中的 `lower` 和 `upper` 值：

```xml
<!-- 原限位 -->
<limit lower="-1.57" upper="1.57" .../>

<!-- 扩大后 -->
<limit lower="-2.0" upper="2.0" .../>
```

### Q: TF 变换获取失败？

确保：
1. RVIZ 和 robot_state_publisher 正在运行
2. 有节点在发布 `/joint_states`
3. 等待 2-3 秒让 TF 树建立