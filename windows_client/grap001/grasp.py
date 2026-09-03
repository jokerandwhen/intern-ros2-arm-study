"""
SoArm101 固定位置抓取执行脚本

位置说明（来自用户实际记录）:
  home:         安全初始位置（臂收起）
  pre_grasp:    物体正上方（夹爪张开，准备下降）
  grasp_close:  下降到物体并闭合夹爪（抓取）
  grasp_up:     抬起物体（回到正上方高度，夹爪闭合）
  place:        移动到放置位置（带着物体）
  place_release:放置位置张开夹爪（释放物体）
  → home:       回到初始位置

抓取序列:
  home → pre_grasp → grasp_close → grasp_up → place → place_release → home
"""
import sys
import os
import time
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arm_controller import SoArmController

POSITIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "positions.json")

def load_positions():
    with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
        saved = json.load(f)
    return {name: {int(k): v for k, v in pos.items()} for name, pos in saved.items()}

def move_to_pose(arm, pose, steps=30, delay=0.03, label=""):
    """平滑移动到指定姿态"""
    if label:
        print(f"  → {label}...", end='', flush=True)
    arm.move_smooth(pose, steps=steps, delay=delay)
    if label:
        print(" done")
    time.sleep(0.3)

def execute_grasp(arm, positions):
    """执行完整抓取序列"""
    
    # 抓取序列定义
    sequence = [
        ("home",         "1/7 回到初始位置"),
        ("pre_grasp",    "2/7 移动到物体正上方（夹爪张开）"),
        ("grasp_close",  "3/7 下降并闭合夹爪（抓取物体）"),
        ("grasp_up",     "4/7 抬起物体"),
        ("place",        "5/7 移动到放置位置"),
        ("place_release","6/7 张开夹爪释放物体"),
        ("home",         "7/7 回到初始位置"),
    ]
    
    # 检查所有位置是否存在
    required = set(name for name, _ in sequence)
    missing = required - set(positions.keys())
    if missing:
        print(f"缺少位置: {', '.join(missing)}")
        return False
    
    print("\n" + "=" * 60)
    print("开始执行抓取任务")
    print("=" * 60)
    print()
    
    # 使能扭矩
    print("使能扭矩...")
    arm.enable_torque()
    time.sleep(0.5)
    
    try:
        for pose_name, desc in sequence:
            pose = positions[pose_name]
            print(f"  [{desc}]")
            move_to_pose(arm, pose, steps=30, delay=0.03)
        
        print()
        print("=" * 60)
        print("抓取任务完成！")
        print("=" * 60)
        return True
        
    except KeyboardInterrupt:
        print("\n\n任务被中断")
        return False
    except Exception as e:
        print(f"\n执行出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        arm.disable_torque()

def main():
    print("=" * 60)
    print("SoArm101 固定位置抓取")
    print("=" * 60)
    
    positions = load_positions()
    print(f"\n已加载 {len(positions)} 个位置:")
    for name, pos in positions.items():
        pos_str = "  ".join([f"M{k}={v}" for k, v in sorted(pos.items())])
        print(f"  {name:<15}: {pos_str}")
    
    print("\n抓取序列:")
    print("  home → pre_grasp → grasp_close → grasp_up → place → place_release → home")
    
    print("\n" + "-" * 60)
    print("确保:")
    print("  1. 物体已放在抓取位置")
    print("  2. 放置区域已清空")
    print("  3. 机械臂活动范围内无障碍物")
    print("-" * 60)
    
    resp = input("\n确认开始抓取? (y/n): ").strip().lower()
    if resp != 'y':
        print("已取消")
        return
    
    arm = SoArmController(port="COM3")
    arm.connect()
    time.sleep(0.3)
    
    # 检查状态
    status = arm.read_status()
    errors = [mid for mid in range(1,7) if status[mid]['status'] != 0]
    if errors:
        print(f"\n警告: 电机 {errors} 有错误状态，尝试继续...")
    
    try:
        execute_grasp(arm, positions)
    finally:
        arm.disconnect()

if __name__ == "__main__":
    main()
