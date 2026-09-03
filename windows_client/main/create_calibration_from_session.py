"""
从最新的校准会话创建校准数据文件
基于终端输出中提取的9个样本
"""

import json
from datetime import datetime
from pathlib import Path

# 创建校准数据（从终端输出中提取）
# 注意：这里只记录了 shoulder_lift 的数据
# 其他关节使用默认值

calibration_data = {
    "timestamp": datetime.now().isoformat(),
    "num_samples": 9,
    "data": [
        {
            "sample_id": 1,
            "timestamp": 1785305100.0,
            "master": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": -176.31,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            },
            "puppet": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": 122.95,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            }
        },
        {
            "sample_id": 2,
            "timestamp": 1785305102.0,
            "master": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": -161.80,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            },
            "puppet": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": 124.62,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            }
        },
        {
            "sample_id": 3,
            "timestamp": 1785305104.0,
            "master": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": -85.41,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            },
            "puppet": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": -153.27,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            }
        },
        {
            "sample_id": 4,
            "timestamp": 1785305106.0,
            "master": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": -86.55,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            },
            "puppet": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": -161.63,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            }
        },
        {
            "sample_id": 5,
            "timestamp": 1785305108.0,
            "master": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": 176.04,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            },
            "puppet": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": 110.73,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            }
        },
        {
            "sample_id": 6,
            "timestamp": 1785305110.0,
            "master": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": 179.82,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            },
            "puppet": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": 108.62,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            }
        },
        {
            "sample_id": 7,
            "timestamp": 1785305112.0,
            "master": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": 124.79,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            },
            "puppet": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": 40.04,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            }
        },
        {
            "sample_id": 8,
            "timestamp": 1785305114.0,
            "master": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": 127.34,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            },
            "puppet": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": 52.62,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            }
        },
        {
            "sample_id": 9,
            "timestamp": 1785305116.0,
            "master": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": 98.42,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            },
            "puppet": {
                "shoulder_pan.pos": 0.0,
                "shoulder_lift.pos": 17.89,
                "elbow_flex.pos": 0.0,
                "wrist_flex.pos": 0.0,
                "wrist_roll.pos": 0.0,
                "gripper.pos": 50.0
            }
        }
    ]
}

# 备份旧文件
CALIBRATION_FILE = Path("calibration_data.json")
if CALIBRATION_FILE.exists():
    import shutil
    backup_file = Path(f"calibration_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    shutil.copy(CALIBRATION_FILE, backup_file)
    print(f"✓ 已备份旧文件到: {backup_file}")

# 保存新文件
with open(CALIBRATION_FILE, 'w') as f:
    json.dump(calibration_data, f, indent=2)

print(f"✓ 已创建新的校准数据文件: {CALIBRATION_FILE}")
print(f"  包含 {calibration_data['num_samples']} 个样本")
print(f"  时间戳: {calibration_data['timestamp']}")
print("\n注意：此文件只包含 shoulder_lift 的校准数据")
print("其他关节使用默认值，建议完成完整校准以获得最佳效果")