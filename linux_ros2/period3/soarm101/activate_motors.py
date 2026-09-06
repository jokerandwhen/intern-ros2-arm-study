"""SO-ARM100 舵机激活脚本 - 重新激活所有舵机"""
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
import time

JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]

def main():
    print("="*70)
    print("SO-ARM100 舵机激活脚本")
    print("="*70)
    
    try:
        # 连接
        print("\n[步骤1] 连接机械臂...")
        config = SOFollowerRobotConfig(port="/dev/ttyACM0")
        robot = SOFollower(config)
        robot.connect()
        print("[OK] 已连接")
        
        # 激活所有舵机
        print("\n[步骤2] 激活所有舵机...")
        print("-"*70)
        
        for name in JOINT_NAMES:
            print(f"\n激活 {name}:")
            
            # 读取当前位置
            try:
                current_pos = robot.bus.read("Present_Position", name)
                print(f"  当前位置: {current_pos:.1f}°")
            except Exception as e:
                print(f"  [ERROR] 无法读取位置: {e}")
                continue
            
            # 尝试禁用再启用力矩
            print("  禁用力矩...")
            try:
                robot.bus.write("Torque_Enable", name, 0)
                time.sleep(0.3)
            except Exception as e:
                print(f"    [WARN] {e}")
            
            print("  启用力矩...")
            try:
                robot.bus.write("Torque_Enable", name, 1)
                time.sleep(0.3)
                print("    [OK] 力矩已启用")
            except Exception as e:
                print(f"    [ERROR] {e}")
                continue
            
            # 尝试写入当前位置（激活控制）
            print("  设置当前位置为目标位置...")
            try:
                robot.bus.write("Goal_Position", name, float(current_pos))
                time.sleep(0.2)
                print("    [OK] 已设置")
            except Exception as e:
                print(f"    [WARN] {e}")
            
            # 尝试小幅度移动测试
            print("  测试移动...")
            target = current_pos + 3 if abs(current_pos) < 30 else current_pos - 3
            try:
                robot.bus.write("Goal_Position", name, float(target))
                time.sleep(0.8)
                
                new_pos = robot.bus.read("Present_Position", name)
                diff = abs(new_pos - current_pos)
                if diff > 1:
                    print(f"    [OK] 移动成功: {current_pos:.1f}° -> {new_pos:.1f}°")
                else:
                    print(f"    [WARN] 未移动 (差值: {diff:.1f}°)")
            except Exception as e:
                print(f"    [ERROR] {e}")
        
        print("\n" + "-"*70)
        
        # 最终状态检查
        print("\n[步骤3] 最终状态检查...")
        print("-"*70)
        
        for name in JOINT_NAMES:
            try:
                pos = robot.bus.read("Present_Position", name)
                print(f"  {name}: {pos:.1f}°")
            except Exception as e:
                print(f"  {name}: [ERROR] {e}")
        
        print("-"*70)
        
        # 断开
        print("\n[OK] 激活完成")
        try:
            robot.disconnect()
        except:
            pass
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()