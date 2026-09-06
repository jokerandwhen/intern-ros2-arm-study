"""清除舵机过载状态"""
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
import time

def main():
    print("="*50)
    print("清除舵机过载状态")
    print("="*50)
    
    try:
        print("\n连接中...")
        config = SOFollowerRobotConfig(port="/dev/ttyACM0")
        robot = SOFollower(config)
        robot.connect()
        print("[OK] 已连接")
        
        print("\n清除所有舵机过载状态...")
        for joint in ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]:
            try:
                # 禁用再启用力矩
                robot.bus.write("Torque_Enable", joint, 0)
                time.sleep(0.1)
                robot.bus.write("Torque_Enable", joint, 1)
                print(f"  {joint}: [OK]")
            except Exception as e:
                print(f"  {joint}: {e}")
        
        print("\n[OK] 清除完成")
        
        # 断开
        try:
            robot.disconnect()
        except:
            pass
            
    except Exception as e:
        print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    main()