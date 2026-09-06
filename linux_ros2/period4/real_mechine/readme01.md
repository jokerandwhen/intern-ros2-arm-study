# SO-ARM101 实机数据记录与分析

本目录用于记录实机舵机数据，辅助校准虚拟模型。

## 文件说明

| 文件 | 说明 |
|------|------|
| `record_real.py` | 独立数据记录脚本（可脱离 ROS2 运行） |
| `analyze_record.py` | 数据分析工具，生成校准参数 |
| `record_*.csv` | 记录的数据文件 |

## 快速开始

### 1. 实机同步 + 数据记录（推荐）

启动 RVIZ 并同步实机数据：

```bash
cd /home/ubuntu/total_internship/period4/period4_ws
bash restart_rviz.sh real record
```

这会：
- 启动 RVIZ 显示虚拟模型
- 读取实机舵机位置 `/dev/ttyACM0`
- 实时同步到虚拟模型
- 自动记录数据到 `real_mechine/record_YYYYMMDD_HHMMSS.csv`

### 2. 仅记录数据（不启动 ROS2）

```bash
cd /home/ubuntu/total_internship/period4/real_mechine

# 记录 60 秒
python3 record_real.py --duration 60 --rate 30

# 记录 5 分钟
python3 record_real.py --duration 300 --rate 30
```

### 3. 数据分析

```bash
cd /home/ubuntu/total_internship/period4/real_mechine

# 分析最新的记录文件
python3 analyze_record.py

# 分析指定文件
python3 analyze_record.py record_20260721_174223.csv

# 生成校准参数（用于更新 xacro）
python3 analyze_record.py --calibrate
```

## 参数说明

### record_real.py

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--port` | `/dev/ttyACM0` | 串口路径 |
| `--duration` | 60 | 记录时长（秒） |
| `--rate` | 30 | 记录频率（Hz） |
| `--ros` | 否 | 同时发布到 ROS2 `/joint_states` |
| `--output` | 自动生成 | 输出文件路径 |

### analyze_record.py

| 参数 | 说明 |
|------|------|
| `csv_path` | CSV 文件路径（默认：最新文件） |
| `--calibrate` | 生成校准参数 |

## 数据格式

CSV 文件包含以下列：

| 列名 | 说明 |
|------|------|
| `timestamp` | 时间戳 |
| `elapsed_s` | 经过时间（秒） |
| `{joint}_deg` | 关节角度（度） |
| `{joint}_rad` | 关节角度（弧度） |

关节：`shoulder_pan`, `shoulder_lift`, `elbow_flex`, `wrist_flex`, `wrist_roll`, `gripper`

## 注意事项

1. **确保只有一个 bridge 实例运行**，否则模型会抖动
2. **记录前检查串口权限**：`ls -l /dev/ttyACM0`
3. **分析结果用于更新 URDF 限位**，确保虚拟模型与实机匹配