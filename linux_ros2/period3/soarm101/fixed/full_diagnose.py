"""SO-ARM100 全面诊断"""
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
import time

JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]

def main():
    print("="*70)
    print("SO-ARM100 全面诊断")
    print("="*70)
    
    print("\n[步骤1] 尝试连接机械臂...")
    try:
        config = SOFollowerRobotConfig(port="/dev/ttyACM0")
        robot = SOFollower(config)
        robot.connect()
        print("[OK] 连接成功")
    except Exception as e:
        print(f"[ERROR] 连接失败: {e}")
        print("\n可能原因:")
        print("  1. 舵机电源未开启")
        print("  2. 串口权限问题 - 运行: sudo chmod 666 /dev/ttyACM0")
        print("  3. 串口号不对 - 检查: ls /dev/ttyACM* /dev/ttyUSB*")
        return
    
    # 读取所有舵机状态
    print("\n[步骤2] 读取所有舵机状态...")
    print("-"*70)
    
    for name in JOINT_NAMES:
        print(f"\n{name}:")
        try:
            # 位置
            pos = robot.bus.read("Present_Position", name)
            print(f"  位置: {pos:.1f}°")
            
            # 温度
            try:
                temp = robot.bus.read("Present_Temperature", name)
                print(f"  温度: {temp}°C", end="")
                if temp > 50:
                    print(" [过热!]")
                else:
                    print()
            except:
                pass
            
            # 电压
            try:
                voltage = robot.bus.read("Present_Voltage", name)
                print(f"  电压: {voltage/10:.1f}V")
            except:
                pass
            
        except Exception as e:
            print(f"  [ERROR] {e}")
            if "Overload" in str(e):
                print("  [状态] 过载保护激活!")
    
    print("-"*70)
    
    # 测试每个舵机响应
    print("\n[步骤3] 测试每个舵机响应...")
    
    for name in JOINT_NAMES:
        print(f"\n测试 {name}:")
        try:
            # 读取当前位置
            current_pos = robot.bus.read("Present_Position", name)
            print(f"  当前位置: {current_pos:.1f}°")
            
            # 尝试小幅度移动
            target = current_pos + 5 if current_pos < 50 else current_pos - 5
            
            try:
                robot.bus.write("Goal_Position", name, float(target))
                print(f"  发送命令: 移动到 {target:.1f}°")
                time.sleep(1)
                
                # 检查是否移动
                new_pos = robot.bus.read("Present_Position", name)
                if abs(new_pos - current_pos) > 1:
                    print(f"  结果: 已移动到 {new_pos:.1f}° [OK]")
                else:
                    print(f"  结果: 未移动 [WARN]")
            except Exception as e:
                print(f"  结果: {e}")
                
        except Exception as e:
            print(f"  [ERROR] {e}")
    
    # 断开
    print("\n" + "="*70)
    print("诊断完成")
    print("="*70)
    
    try:
        robot.disconnect()
    except:
        pass

if __name__ == "__main__":
    main()