"""
移动到指定位置（测试用）
用法: python goto.py <位置名称>
例如: python goto.py grasp_close
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
    if os.path.exists(POSITIONS_FILE):
        with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def main():
    if len(sys.argv) < 2:
        print("用法: python goto.py <位置名称>")
        print("可用位置:")
        positions = load_positions()
        for name in positions:
            print(f"  {name}")
        return
    
    name = sys.argv[1]
    positions = load_positions()
    
    if name not in positions:
        print(f"❌ 位置 '{name}' 不存在")
        print(f"可用位置: {', '.join(positions.keys())}")
        return
    
    pose = {int(k): v for k, v in positions[name].items()}
    
    print(f"移动到位置: {name}")
    print(f"目标: {pose}")
    
    arm = SoArmController(port="COM3")
    arm.connect()
    time.sleep(0.3)
    
    # 检查状态
    status = arm.read_status()
    for mid in range(1, 7):
        if status[mid]['status'] != 0:
            print(f"⚠ 电机{mid}状态异常: 0x{status[mid]['status']:02X}")
    
    arm.enable_torque()
    time.sleep(0.3)
    
    print("\n平滑移动中...")
    arm.move_smooth(pose, steps=30, delay=0.03)
    time.sleep(0.5)
    
    # 读取实际位置
    actual = arm.read_all_positions()
    print("\n实际到达位置:")
    for mid in range(1, 7):
        target = pose.get(mid, 0)
        a = actual.get(mid, 0)
        diff = abs(a - target)
        print(f"  {arm.MOTOR_NAMES[mid]:<15} 目标={target:4d} 实际={a:4d} 差={diff:3d}")
    
    print("\n✓ 到达目标位置")
    print("按Enter回到初始位置并退出...")
    input()
    
    # 回到启动时的位置
    home = arm.read_all_positions()
    print("回到启动位置...")
    arm.move_smooth(home, steps=20, delay=0.03)
    arm.disconnect()

if __name__ == "__main__":
    main()
