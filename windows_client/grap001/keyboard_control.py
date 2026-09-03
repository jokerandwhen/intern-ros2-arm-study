"""
键盘控制机械臂 - 自由运动控制
使用键盘按键控制每个关节的运动

按键说明:
  Q/A  - 关节1 (shoulder_pan)  减/加
  W/S  - 关节2 (shoulder_lift) 减/加
  E/D  - 关节3 (elbow_flex)    减/加
  R/F  - 关节4 (wrist_flex)    减/加
  T/G  - 关节5 (wrist_roll)    减/加
  Y/H  - 关节6 (gripper)       减/加 (张开/闭合)
  O    - 完全张开夹爪
  C    - 闭合夹爪
  Z    - 减小步长
  X    - 增大步长
  空格  - 读取并显示当前位置
  P    - 保存当前位置到positions.json
  M    - 回到初始位置
  K    - 使能/禁用扭矩切换（禁用时可手动移动）
  Ctrl+C - 退出
"""
import sys
import os
import time
import json
import msvcrt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arm_controller import SoArmController

POSITIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "positions.json")

def get_key():
    """非阻塞读取键盘按键"""
    if msvcrt.kbhit():
        key = msvcrt.getch()
        # 处理特殊键（方向键等）
        if key in (b'\x00', b'\xe0'):
            msvcrt.getch()  # 跳过第二个字节
            return None
        try:
            return key.decode('utf-8').lower()
        except:
            return None
    return None

def load_positions():
    if os.path.exists(POSITIONS_FILE):
        with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_positions(positions):
    with open(POSITIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(positions, f, indent=2, ensure_ascii=False)

def main():
    print("=" * 60)
    print("SoArm101 键盘自由控制")
    print("=" * 60)
    
    arm = SoArmController(port="COM3")
    arm.connect()
    
    # 读取初始位置作为home
    time.sleep(0.5)
    home_pos = arm.read_all_positions()
    
    # 读取状态
    status = arm.read_status()
    print("\n电机状态：")
    for mid in range(1, 7):
        s = status[mid]
        err = "OK" if s['status'] == 0 else "ERR"
        print(f"  [{err}] {arm.MOTOR_NAMES[mid]:<15} V={s['voltage']:.1f}V T={s['temp']}°C")
    
    # 使能扭矩
    print("\n使能扭矩...")
    arm.enable_torque()
    time.sleep(0.3)
    
    current_pos = arm.read_all_positions()
    
    step = 50  # 默认步长
    
    key_map = {
        'q': (1, -1), 'a': (1, 1),
        'w': (2, -1), 's': (2, 1),
        'e': (3, -1), 'd': (3, 1),
        'r': (4, -1), 'f': (4, 1),
        't': (5, -1), 'g': (5, 1),
        'y': (6, -1), 'h': (6, 1),
    }
    
    torque_enabled = True
    
    print("\n" + "=" * 60)
    print(__doc__)
    print("=" * 60)
    print(f"\n当前步长: {step} (按Z减小/X增大)")
    print("按住按键持续运动，Ctrl+C退出\n")
    
    try:
        while True:
            key = get_key()
            
            if key is None:
                time.sleep(0.02)
                continue
            
            # 步长调整
            if key == 'z':
                step = max(1, step // 2)
                print(f"步长: {step}   ")
                continue
            if key == 'x':
                step = min(500, step * 2)
                print(f"步长: {step}   ")
                continue
            
            # 扭矩开关
            if key == 'k':
                torque_enabled = not torque_enabled
                if torque_enabled:
                    arm.enable_torque()
                    print("✓ 扭矩已使能       ")
                else:
                    arm.disable_torque()
                    print("✓ 扭矩已禁用（可手动移动）")
                time.sleep(0.2)
                continue
            
            # 读取当前位置
            if key == ' ':
                current_pos = arm.read_all_positions()
                print("\n当前位置:")
                for mid in range(1, 7):
                    print(f"  {arm.MOTOR_NAMES[mid]:<15} = {current_pos[mid]}")
                print()
                continue
            
            # 保存位置
            if key == 'p':
                positions = load_positions()
                print("\n输入位置名称（如home/pre_grasp/grasp_down等）: ", end='', flush=True)
                name = input().strip()
                if name:
                    current_pos = arm.read_all_positions()
                    positions[name] = {str(mid): current_pos[mid] for mid in range(1, 7)}
                    save_positions(positions)
                    print(f"✓ 位置 '{name}' 已保存")
                continue
            
            # 回到home
            if key == 'm':
                print("\n回到初始位置...")
                arm.move_smooth(home_pos, steps=30, delay=0.03)
                current_pos = home_pos.copy()
                print("✓ 已回到初始位置")
                continue
            
            # 张开夹爪
            if key == 'o':
                print("张开夹爪...     ")
                arm.open_gripper(1258)
                current_pos[6] = 1258
                continue
            
            # 闭合夹爪
            if key == 'c':
                print("闭合夹爪...     ")
                arm.close_gripper(1740)
                current_pos[6] = 1740
                continue
            
            # 关节控制
            if key in key_map:
                joint, direction = key_map[key]
                if not torque_enabled:
                    print("⚠ 请先按K使能扭矩")
                    continue
                
                new_pos = current_pos.copy()
                new_val = current_pos[joint] + direction * step
                new_val = max(0, min(4095, new_val))
                new_pos[joint] = new_val
                
                arm._sync_write_positions(new_pos)
                current_pos[joint] = new_val
                
                # 显示当前关节位置
                print(f"  {arm.MOTOR_NAMES[joint]} = {new_val}     ", end='\r')
                continue
    
    except KeyboardInterrupt:
        pass
    
    finally:
        print("\n\n回到安全位置...")
        try:
            arm.move_smooth(home_pos, steps=20, delay=0.03)
        except:
            pass
        arm.disconnect()
        print("完成")

if __name__ == "__main__":
    main()
