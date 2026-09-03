"""
位置记录脚本
手动将机械臂摆到指定位置，按Enter记录该位置
记录的位置会保存到 positions.json
"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arm_controller import SoArmController

POSITIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "positions.json")

# 默认抓取流程位置名称
DEFAULT_KEYS = [
    "home",         # 初始/归位位置
    "pre_grasp",    # 抓取预备位置（物体上方）
    "grasp_down",   # 下降到物体位置
    "grasp_close",  # 闭合夹爪抓取
    "grasp_up",     # 抬起物体
    "place_down",   # 移动到放置位置上方
    "place_release",# 张开夹爪放置
    "back_home",    # 回到初始位置
]

def load_positions():
    """加载已保存的位置"""
    if os.path.exists(POSITIONS_FILE):
        with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_positions(positions):
    """保存位置到文件"""
    with open(POSITIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(positions, f, indent=2, ensure_ascii=False)
    print(f"✓ 位置已保存到 {POSITIONS_FILE}")

def main():
    print("=" * 60)
    print("SoArm101 抓取位置记录工具")
    print("=" * 60)
    print()
    
    arm = SoArmController(port="COM3")
    arm.connect()
    
    # 读取状态
    print("\n电机状态：")
    status = arm.read_status()
    for mid in range(1, 7):
        s = status[mid]
        err = "⚠" if s['status'] != 0 else "✓"
        print(f"  {err} {arm.MOTOR_NAMES[mid]:<15} V={s['voltage']:.1f}V T={s['temp']}°C status=0x{s['status']:02X}")
    
    # 加载已有位置
    positions = load_positions()
    if positions:
        print(f"\n已保存 {len(positions)} 个位置: {', '.join(positions.keys())}")
    
    # 禁用扭矩以便手动移动
    print("\n禁用扭矩，可以手动移动机械臂...")
    arm.disable_torque()
    
    print("\n" + "=" * 60)
    print("位置记录说明：")
    print("  - 输入位置名称后按Enter，会记录当前所有关节角度")
    print("  - 输入 'list' 查看已记录的位置")
    print("  - 输入 'read' 读取当前位置（不保存）")
    print("  - 输入 'delete <name>' 删除某个位置")
    print("  - 输入 'quit' 退出")
    print("=" * 60)
    
    while True:
        print()
        cmd = input("输入位置名称或命令: ").strip()
        
        if cmd.lower() == 'quit':
            break
        elif cmd.lower() == 'list':
            if not positions:
                print("  (暂无记录)")
            else:
                for name, pos in positions.items():
                    pos_str = "  ".join([f"M{mid}={v}" for mid, v in sorted(pos.items())])
                    print(f"  {name}: {pos_str}")
            continue
        elif cmd.lower() == 'read':
            current = arm.read_all_positions()
            for mid in range(1, 7):
                print(f"  {arm.MOTOR_NAMES[mid]:<15} = {current[mid]}")
            continue
        elif cmd.lower().startswith('delete '):
            name = cmd[7:].strip()
            if name in positions:
                del positions[name]
                save_positions(positions)
                print(f"  已删除 '{name}'")
            else:
                print(f"  位置 '{name}' 不存在")
            continue
        elif not cmd:
            continue
        
        # 记录位置
        current = arm.read_all_positions()
        positions[cmd] = {str(mid): current[mid] for mid in range(1, 7)}
        save_positions(positions)
        
        print(f"  已记录位置 '{cmd}':")
        for mid in range(1, 7):
            print(f"    {arm.MOTOR_NAMES[mid]:<15} = {current[mid]}")
    
    arm.disconnect()
    print("\n完成！可以运行 grasp.py 执行抓取")

if __name__ == "__main__":
    main()
