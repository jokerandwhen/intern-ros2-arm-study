"""
SoArm101 调试程序
用于测试机械臂连接和基本功能
"""

import time
import numpy as np
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def test_arm(port, name):
    """测试单个机械臂"""
    print(f"\n{'='*60}")
    print(f"测试 {name} ({port})")
    print('='*60)
    
    try:
        # 1. 连接
        print(f"[INFO] 正在连接 {name}...")
        config = SOFollowerRobotConfig(port=port)
        robot = SOFollower(config)
        robot.connect()
        print(f"[OK] {name} 连接成功")
        
        # 2. 读取当前状态
        print(f"\n[INFO] 读取 {name} 当前状态...")
        obs = robot.get_observation()
        print(f"[DEBUG] 观测数据类型: {type(obs)}")
        print(f"[DEBUG] 观测数据: {obs}")
        
        # 3. 提取关节角度
        if isinstance(obs, dict):
            print(f"[DEBUG] 字典键: {list(obs.keys())}")
            joints = [
                obs.get("shoulder_pan.pos", 0.0),
                obs.get("shoulder_lift.pos", 0.0),
                obs.get("elbow_flex.pos", 0.0),
                obs.get("wrist_flex.pos", 0.0),
                obs.get("wrist_roll.pos", 0.0),
                obs.get("gripper.pos", 0.0)
            ]
            print(f"[INFO] 关节角度: {joints}")
        
        # 4. 测试发送动作
        print(f"\n[INFO] 测试发送动作...")
        test_action = {
            "shoulder_pan.pos": 0.0,
            "shoulder_lift.pos": -0.3,
            "elbow_flex.pos": 0.5,
            "wrist_flex.pos": 0.0,
            "wrist_roll.pos": 0.0,
            "gripper.pos": 0.0
        }
        print(f"[DEBUG] 发送动作: {test_action}")
        result = robot.send_action(test_action)
        print(f"[DEBUG] 发送结果: {result}")
        
        time.sleep(2)  # 等待2秒
        
        # 5. 再次读取状态
        print(f"\n[INFO] 再次读取状态...")
        obs = robot.get_observation()
        if isinstance(obs, dict):
            joints = [
                obs.get("shoulder_pan.pos", 0.0),
                obs.get("shoulder_lift.pos", 0.0),
                obs.get("elbow_flex.pos", 0.0),
                obs.get("wrist_flex.pos", 0.0),
                obs.get("wrist_roll.pos", 0.0),
                obs.get("gripper.pos", 0.0)
            ]
            print(f"[INFO] 关节角度: {joints}")
        
        # 6. 断开连接
        robot.disconnect()
        print(f"\n[OK] {name} 测试完成")
        
    except Exception as e:
        print(f"[ERROR] {name} 测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("="*60)
    print("SoArm101 机械臂调试程序")
    print("="*60)
    
    # 测试COM3
    test_arm("COM3", "主臂")
    
    # 测试COM4
    test_arm("COM4", "辅助臂")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == "__main__":
    main()