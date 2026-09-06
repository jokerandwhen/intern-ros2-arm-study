"""SO-ARM100 姿态分析工具"""
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
POSES_FILE = os.path.join(SCRIPT_DIR, "poses.json")
JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]

def load_poses():
    """加载已保存的姿态"""
    if os.path.exists(POSES_FILE):
        with open(POSES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get("poses", [])
    return []

def print_all_poses(poses):
    """打印所有姿态"""
    if not poses:
        print("\n暂无记录的姿态")
        return
    
    print("\n" + "="*70)
    print(f"已记录的姿态 (共 {len(poses)} 个)")
    print("="*70)
    
    for i, pose in enumerate(poses):
        print(f"\n姿态 {i+1}: {pose['name']}")
        print(f"  时间: {pose['timestamp']}")
        print("  关节角度:")
        for name in JOINT_NAMES:
            angle = pose['angles'].get(name, 0)
            print(f"    {name:15s}: {angle:7.1f}°")
    
    print("="*70)

def analyze_differences(poses):
    """分析姿态差异"""
    if len(poses) < 2:
        print("\n至少需要2个姿态才能分析差异")
        return
    
    print("\n" + "="*70)
    print("姿态差异分析")
    print("="*70)
    
    for i in range(len(poses) - 1):
        p1, p2 = poses[i], poses[i+1]
        print(f"\n姿态 {i+1} ({p1['name']}) -> 姿态 {i+2} ({p2['name']}):")
        print("-"*50)
        total_change = 0
        for name in JOINT_NAMES:
            a1 = p1['angles'].get(name, 0)
            a2 = p2['angles'].get(name, 0)
            diff = a2 - a1
            total_change += abs(diff)
            print(f"  {name:15s}: {a1:7.1f}° -> {a2:7.1f}° (变化: {diff:+7.1f}°)")
        print(f"  总变化量: {total_change:.1f}°")
    
    print("="*70)

def compare_two_poses(poses, idx1, idx2):
    """比较两个指定姿态"""
    if len(poses) < 2:
        print("\n至少需要2个姿态才能比较")
        return
    
    if idx1 < 0 or idx1 >= len(poses) or idx2 < 0 or idx2 >= len(poses):
        print(f"\n索引超出范围 (可用: 1-{len(poses)})")
        return
    
    p1, p2 = poses[idx1], poses[idx2]
    print("\n" + "="*70)
    print(f"姿态比较: {p1['name']} vs {p2['name']}")
    print("="*70)
    
    for name in JOINT_NAMES:
        a1 = p1['angles'].get(name, 0)
        a2 = p2['angles'].get(name, 0)
        diff = a2 - a1
        print(f"  {name:15s}: {a1:7.1f}° vs {a2:7.1f}° (差异: {diff:+7.1f}°)")
    
    print("="*70)

def export_to_csv(poses):
    """导出姿态到CSV"""
    if not poses:
        print("\n暂无姿态可导出")
        return
    
    csv_file = os.path.join(SCRIPT_DIR, "poses.csv")
    with open(csv_file, 'w') as f:
        f.write("name,timestamp," + ",".join(JOINT_NAMES) + "\n")
        for pose in poses:
            angles = [str(pose['angles'].get(name, 0)) for name in JOINT_NAMES]
            f.write(f"{pose['name']},{pose['timestamp']}," + ",".join(angles) + "\n")
    
    print(f"\n已导出到: {csv_file}")

def main():
    poses = load_poses()
    
    print("="*70)
    print("SO-ARM100 姿态分析工具")
    print("="*70)
    
    while True:
        print("\n命令:")
        print("  1 - 显示所有姿态")
        print("  2 - 分析姿态差异")
        print("  3 - 比较两个姿态")
        print("  4 - 导出为CSV")
        print("  q - 退出")
        
        cmd = input("\n请输入命令: ").strip()
        
        if cmd == '1':
            print_all_poses(poses)
        elif cmd == '2':
            analyze_differences(poses)
        elif cmd == '3':
            try:
                idx1 = int(input("输入第一个姿态编号: ")) - 1
                idx2 = int(input("输入第二个姿态编号: ")) - 1
                compare_two_poses(poses, idx1, idx2)
            except ValueError:
                print("请输入有效数字")
        elif cmd == '4':
            export_to_csv(poses)
        elif cmd in 'qQ':
            print("退出")
            break
        else:
            print("未知命令")

if __name__ == "__main__":
    main()