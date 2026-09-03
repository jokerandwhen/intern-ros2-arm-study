"""
搜索位置标定脚本
记录机械臂在搜索物体时需要移动到的几个位置

搜索位置要求：
  - 夹爪朝下，摄像头俯视桌面
  - 几个位置覆盖桌面的不同区域
  - 建议记录3-5个搜索位置

用法:
  python setup_search.py
"""
import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "grap001"))

from arm_controller import SoArmController

SEARCH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_poses.json")

def load_search_poses():
    if os.path.exists(SEARCH_FILE):
        with open(SEARCH_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_search_poses(poses):
    with open(SEARCH_FILE, 'w', encoding='utf-8') as f:
        json.dump(poses, f, indent=2, ensure_ascii=False)
    print(f"✓ 已保存到 {SEARCH_FILE}")

def main():
    print("=" * 60)
    print("搜索位置标定工具")
    print("=" * 60)
    print()
    print("说明:")
    print("  搜索位置是机械臂在搜索物体时停靠的几个位置")
    print("  每个位置夹爪朝下，摄像头俯视桌面")
    print("  建议记录3-5个位置覆盖桌面不同区域")
    print()
    print("操作:")
    print("  1. 用 keyboard_control.py 移动机械臂到搜索位置")
    print("  2. 在这里输入位置名称（如 search_1, search_2...）")
    print("  3. 程序自动读取并保存当前关节角度")
    print("  4. 重复记录多个位置")
    print("  5. 输入 quit 退出")
    print()
    
    arm = SoArmController(port="COM3")
    arm.connect()
    time.sleep(0.3)
    
    poses = load_search_poses()
    if poses:
        print(f"已有 {len(poses)} 个搜索位置:")
        for name, pos in poses.items():
            print(f"  {name}: {pos}")
    
    arm.disable_torque()
    print("\n扭矩已禁用，可以手动移动机械臂")
    
    while True:
        print()
        cmd = input("输入位置名称（如 search_1）或 quit: ").strip()
        
        if cmd.lower() == 'quit':
            break
        if not cmd:
            continue
        
        # 读取当前位置
        pos = arm.read_all_positions()
        poses[cmd] = {str(k): v for k, v in pos.items()}
        save_search_poses(poses)
        
        print(f"  已记录 '{cmd}':")
        for mid in range(1, 7):
            print(f"    {arm.MOTOR_NAMES[mid]:<15} = {pos[mid]}")
    
    arm.disconnect()
    
    print(f"\n共记录了 {len(poses)} 个搜索位置")
    print("现在可以运行: python vision_grasp.py")

if __name__ == "__main__":
    main()
