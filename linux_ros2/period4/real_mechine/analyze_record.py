#!/usr/bin/env python3
"""SO-ARM101 实机数据分析工具
读取记录CSV，分析关节范围、运动轨迹，辅助校准虚拟模型。

用法:
  # 分析最近的记录文件
  python3 analyze_record.py

  # 指定文件
  python3 analyze_record.py record_20260721_120000.csv

  # 生成校准参数
  python3 analyze_record.py --calibrate
"""
import csv
import math
import os
import sys
import argparse
import glob
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex",
               "wrist_flex", "wrist_roll", "gripper"]

# URDF中的关节限位(rad)
URDF_LIMITS = {
    "shoulder_pan": (-3.14159, 3.14159),
    "shoulder_lift": (-3.14159, 3.14159),
    "elbow_flex": (-3.14159, 3.14159),
    "wrist_flex": (-1.5708, 1.5708),
    "wrist_roll": (-3.14159, 3.14159),
    "gripper": (0.0, 0.014),
}


def find_latest_record():
    """查找最新的记录文件"""
    pattern = os.path.join(SCRIPT_DIR, "record_*.csv")
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None


def load_csv(csv_path):
    """加载CSV数据"""
    data = {name: {"deg": [], "rad": []} for name in JOINT_NAMES}
    timestamps = []
    elapsed = []

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            timestamps.append(row.get("timestamp", ""))
            elapsed.append(float(row.get("elapsed_s", 0)))
            for name in JOINT_NAMES:
                deg_key = f"{name}_deg"
                if deg_key in row:
                    data[name]["deg"].append(float(row[deg_key]))

    return data, timestamps, elapsed


def analyze_record(csv_path):
    """分析记录数据"""
    print(f"\n{'='*70}")
    print(f"SO-ARM101 实机数据分析")
    print(f"{'='*70}")
    print(f"文件: {csv_path}")
    print(f"时间: {datetime.fromtimestamp(os.path.getmtime(csv_path))}")
    print()

    data, timestamps, elapsed = load_csv(csv_path)
    total_samples = len(elapsed)
    total_duration = elapsed[-1] if elapsed else 0
    print(f"总样本: {total_samples}")
    print(f"总时长: {total_duration:.1f}s")
    print(f"平均频率: {total_samples/total_duration:.1f}Hz\n")

    # 各关节分析
    print(f"{'关节':<16s} {'最小值(°)':>10s} {'最大值(°)':>10s} {'范围(°)':>10s} "
          f"{'URDF限位(rad)':>20s} {'状态':>6s}")
    print("-" * 75)

    for name in JOINT_NAMES:
        degs = data[name]["deg"]
        if not degs:
            continue

        min_deg = min(degs)
        max_deg = max(degs)
        range_deg = max_deg - min_deg

        # URDF限位
        urdf_name = name.replace("shoulder_pan", "joint1") \
                        .replace("shoulder_lift", "joint2") \
                        .replace("elbow_flex", "joint3") \
                        .replace("wrist_flex", "joint4") \
                        .replace("wrist_roll", "joint5") \
                        .replace("gripper", "joint6")

        urdf_limits = URDF_LIMITS.get(name, (-3.14, 3.14))
        if name == "gripper":
            urdf_min_deg = urdf_limits[0] * 100 / 0.014
            urdf_max_deg = urdf_limits[1] * 100 / 0.014
        else:
            urdf_min_deg = math.degrees(urdf_limits[0])
            urdf_max_deg = math.degrees(urdf_limits[1])

        status = "OK"
        if min_deg < urdf_min_deg - 1 or max_deg > urdf_max_deg + 1:
            status = "超限!"

        print(f"{name:<16s} {min_deg:>10.1f} {max_deg:>10.1f} {range_deg:>10.1f} "
              f"[{urdf_min_deg:.0f}, {urdf_max_deg:.0f}]{'':>6s} {status:>6s}")

    print()
    print("=" * 70)
    print("校准建议")
    print("=" * 70)

    suggestions = []
    for name in JOINT_NAMES:
        degs = data[name]["deg"]
        if not degs:
            continue
        avg = sum(degs) / len(degs)
        min_d = min(degs)
        max_d = max(degs)

        urdf_limits = URDF_LIMITS.get(name, (-3.14, 3.14))
        if name == "gripper":
            urdf_min = urdf_limits[0] * 100 / 0.014
            urdf_max = urdf_limits[1] * 100 / 0.014
        else:
            urdf_min = math.degrees(urdf_limits[0])
            urdf_max = math.degrees(urdf_limits[1])

        if min_d < urdf_min - 0.5:
            suggestions.append(
                f"  {name}: 实机最小值({min_d:.1f}°) < URDF限位({urdf_min:.0f}°), "
                f"建议扩大URDF下限")
        if max_d > urdf_max + 0.5:
            suggestions.append(
                f"  {name}: 实机最大值({max_d:.1f}°) > URDF限位({urdf_max:.0f}°), "
                f"建议扩大URDF上限")

    if suggestions:
        for s in suggestions:
            print(s)
    else:
        print("  无校准建议, 模型限位与实机范围匹配")

    print()
    print("=" * 70)
    print("校准参数参考 (可用于更新 xacro limit)")

    for name in JOINT_NAMES:
        degs = data[name]["deg"]
        if not degs:
            continue
        min_d = min(degs)
        max_d = max(degs)
        if name == "gripper":
            print(f"  {name}: lower={min_d/100*0.014:.4f} upper={max_d/100*0.014:.4f}")
        else:
            print(f"  {name}: lower={math.radians(min_d):.4f} upper={math.radians(max_d):.4f}")

    print()
    return data


def generate_calibration(data):
    """生成校准参数"""
    print("\n" + "=" * 70)
    print("校准参数 (用于 soarm101.xacro)")
    print("=" * 70)

    for name in JOINT_NAMES:
        degs = data[name]["deg"]
        if not degs:
            continue
        min_d = min(degs)
        max_d = max(degs)
        # 扩大10%余量
        margin = (max_d - min_d) * 0.1
        min_safe = min_d - margin
        max_safe = max_d + margin

        if name == "gripper":
            print(f"  <limit lower=\"{min_safe/100*0.014:.4f}\" "
                  f"upper=\"{max_safe/100*0.014:.4f}\" "
                  f"effort=\"5\" velocity=\"0.05\"/>  <!-- {name} -->")
        else:
            print(f"  <limit lower=\"{math.radians(min_safe):.4f}\" "
                  f"upper=\"{math.radians(max_safe):.4f}\" "
                  f"effort=\"15\" velocity=\"3.14\"/>  <!-- {name} -->")


def main():
    parser = argparse.ArgumentParser(description='SO-ARM101 实机数据分析工具')
    parser.add_argument('csv_path', nargs='?', default=None, help='CSV文件路径(默认: 最新文件)')
    parser.add_argument('--calibrate', action='store_true', help='生成校准参数')
    args = parser.parse_args()

    csv_path = args.csv_path
    if not csv_path:
        csv_path = find_latest_record()
        if not csv_path:
            print("[ERROR] 未找到记录文件, 请先运行 record_real.py")
            sys.exit(1)

    data = analyze_record(csv_path)

    if args.calibrate:
        generate_calibration(data)


if __name__ == "__main__":
    main()