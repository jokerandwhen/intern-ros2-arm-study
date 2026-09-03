"""
从终端输出中提取校准数据并保存
"""

import json
from datetime import datetime
from pathlib import Path

# 从终端输出中提取的数据
calibration_samples = [
    # 样本1
    {
        "sample_id": 1,
        "master": {
            "shoulder_lift.pos": -176.31
        },
        "puppet": {
            "shoulder_lift.pos": 122.95
        }
    },
    # 样本2
    {
        "sample_id": 2,
        "master": {
            "shoulder_lift.pos": -161.80
        },
        "puppet": {
            "shoulder_lift.pos": 124.62
        }
    },
    # 样本3
    {
        "sample_id": 3,
        "master": {
            "shoulder_lift.pos": -85.41
        },
        "puppet": {
            "shoulder_lift.pos": -153.27
        }
    },
    # 样本4
    {
        "sample_id": 4,
        "master": {
            "shoulder_lift.pos": -86.55
        },
        "puppet": {
            "shoulder_lift.pos": -161.63
        }
    },
    # 样本5
    {
        "sample_id": 5,
        "master": {
            "shoulder_lift.pos": 176.04
        },
        "puppet": {
            "shoulder_lift.pos": 110.73
        }
    },
    # 样本6
    {
        "sample_id": 6,
        "master": {
            "shoulder_lift.pos": 179.82
        },
        "puppet": {
            "shoulder_lift.pos": 108.62
        }
    },
    # 样本7
    {
        "sample_id": 7,
        "master": {
            "shoulder_lift.pos": 124.79
        },
        "puppet": {
            "shoulder_lift.pos": 40.04
        }
    },
    # 样本8
    {
        "sample_id": 8,
        "master": {
            "shoulder_lift.pos": 127.34
        },
        "puppet": {
            "shoulder_lift.pos": 52.62
        }
    },
    # 样本9
    {
        "sample_id": 9,
        "master": {
            "shoulder_lift.pos": 98.42
        },
        "puppet": {
            "shoulder_lift.pos": 17.89
        }
    }
]

print("="*70)
print("分析 shoulder_lift 映射方向")
print("="*70)

# 提取 shoulder_lift 数据
puppet_values = [s['puppet']['shoulder_lift.pos'] for s in calibration_samples]
master_values = [s['master']['shoulder_lift.pos'] for s in calibration_samples]

print(f"\n样本数据：")
for i, (p, m) in enumerate(zip(puppet_values, master_values), 1):
    print(f"  样本{i}: 辅助臂 {p:7.2f}° → 主臂 {m:8.2f}°")

print(f"\n统计分析：")
print(f"  辅助臂范围: [{min(puppet_values):.2f}°, {max(puppet_values):.2f}°]")
print(f"  主臂范围: [{min(master_values):.2f}°, {max(master_values):.2f}°]")

# 计算线性映射
import numpy as np
puppet_arr = np.array(puppet_values)
master_arr = np.array(master_values)

# 计算相关性
correlation = np.corrcoef(puppet_arr, master_arr)[0, 1]
print(f"  相关系数: {correlation:.4f}")

# 计算线性回归
slope, intercept = np.polyfit(puppet_arr, master_arr, 1)
print(f"  斜率: {slope:.4f}")
print(f"  截距: {intercept:.4f}")

# 判断方向
if slope > 0:
    print(f"\n✓ shoulder_lift 映射方向正确！（斜率 > 0）")
    print(f"  辅助臂向上 → 主臂向上")
else:
    print(f"\n⚠️ shoulder_lift 映射方向反转！（斜率 < 0）")
    print(f"  辅助臂向上 → 主臂向下")

print("\n建议：运行 python smart_mapping.py 测试效果")