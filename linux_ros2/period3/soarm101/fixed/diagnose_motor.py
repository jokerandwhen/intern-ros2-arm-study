"""SO-ARM100 舵机诊断和修复工具"""
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
import time

JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]

def main():
    print("="*70)
    print("SO-ARM100 舵机诊断和修复工具")
    print("="*70)
    
    try:
        # 连接机械臂
        print("\n[步骤1] 连接机械臂...")
        config = SOFollowerRobotConfig(port="/dev/ttyACM0")
        robot = SOFollower(config)
        robot.connect()
        print("[OK] 连接成功")
        
        # 读取所有舵机状态
        print("\n[步骤2] 读取舵机状态...")
        print("-"*70)
        
        for i, name in enumerate(JOINT_NAMES):
            try:
                # 读取当前位置
                pos = robot.bus.read("Present_Position", name)
                
                # 尝试读取其他状态
                try:
                    temp = robot.bus.read("Present_Temperature", name)
                except:
                    temp = "N/A"
                
                try:
                    voltage = robot.bus.read("Present_Voltage", name)
                except:
                    voltage = "N/A"
                
                try:
                    load = robot.bus.read("Present_Load", name)
                except:
                    load = "N/A"
                
                print(f"  {i+1}. {name:15s}: 位置={pos:.1f}° 温度={temp} 电压={voltage} 负载={load}")
                
            except Exception as e:
                print(f"  {i+1}. {name:15s}: [ERROR] {e}")
        
        print("-"*70)
        
        # 修复问题舵机
        print("\n[步骤3] 尝试修复问题舵机...")
        problem_joint = "elbow_flex"
        
        print(f"\n修复关节: {problem_joint}")
        
        # 方法1: 禁用再启用
        print("\n  方法1: 禁用再启用力矩...")
        try:
            robot.bus.write("Torque_Enable", problem_joint, 0)
            time.sleep(0.5)
            robot.bus.write("Torque_Enable", problem_joint, 1)
            print("  [OK] 力矩已重置")
        except Exception as e:
            print(f"  [FAIL] {e}")
        
        # 方法2: 设置到当前位置
        print("\n  方法2: 设置到当前位置...")
        try:
            current_pos = robot.bus.read("Present_Position", problem_joint)
            robot.bus.write("Goal_Position", problem_joint, current_pos)
            print(f"  [OK] 已设置目标位置为当前位置: {current_pos:.1f}°")
        except Exception as e:
            print(f"  [FAIL] {e}")
        
        # 方法3: 小幅度移动测试
        print("\n  方法3: 小幅度移动测试...")
        try:
            current_pos = robot.bus.read("Present_Position", problem_joint)
            # 尝试移动+2度
            target = current_pos + 2
            robot.bus.write("Goal_Position", problem_joint, target)
            print(f"  [INFO] 目标位置: {target:.1f}°")
            time.sleep(1)
            
            # 检查是否移动
            new_pos = robot.bus.read("Present_Position", problem_joint)
            if abs(new_pos - current_pos) > 0.5:
                print(f"  [OK] 舵机已响应，当前位置: {new_pos:.1f}°")
            else:
                print(f"  [WARN] 舵机未移动，可能仍有问题")
        except Exception as e:
            print(f"  [FAIL] {e}")
        
        # 重新读取状态
        print("\n[步骤4] 重新读取状态...")
        try:
            pos = robot.bus.read("Present_Position", problem_joint)
            print(f"  {problem_joint}: {pos:.1f}°")
        except Exception as e:
            print(f"  [ERROR] {e}")
        
        # 断开连接
        print("\n[INFO] 断开连接...")
        try:
            robot.disconnect()
        except:
            pass
        
        print("\n[OK] 诊断完成")
        print("\n提示: 如果舵机仍然不动，可能需要:")
        print("  1. 检查舵机电源连接")
        print("  2. 检查机械结构是否卡住")
        print("  3. 舵机可能需要更换")
        
    except Exception as e:
        print(f"\n[ERROR] 诊断失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()