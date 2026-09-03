"""
远程操控（无归位版本）
跳过归位步骤，避免电机过载
"""

import time
import numpy as np
import json
from datetime import datetime
from pathlib import Path
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

# 配置
MASTER_ARM_PORT = "COM3"
PUPPET_ARM_PORT = "COM4"
DATA_DIR = Path("dataset")
DATA_DIR.mkdir(exist_ok=True)

def teleop_no_home():
    """远程操控（无归位）"""
    
    # 连接主臂
    print(f"\n[INFO] 正在连接主臂（{MASTER_ARM_PORT}）...")
    master_config = SOFollowerRobotConfig(port=MASTER_ARM_PORT)
    master = SOFollower(master_config)
    master.connect()
    print("[OK] 主臂连接成功")
    
    # 连接辅助臂
    print(f"\n[INFO] 正在连接辅助臂（{PUPPET_ARM_PORT}）...")
    puppet_config = SOFollowerRobotConfig(port=PUPPET_ARM_PORT)
    puppet = SOFollower(puppet_config)
    puppet.connect()
    print("[OK] 辅助臂连接成功")
    
    print("\n" + "="*50)
    print("远程操控模式（无归位）")
    print("="*50)
    print("说明：")
    print("  - 辅助臂（COM4）：你手动操作这个臂")
    print("  - 主臂（COM3）：会自动跟随")
    print("  - 按 Ctrl+C 退出")
    print("="*50 + "\n")
    
    episode_id = 1
    episode_data = []
    start_time = time.time()
    
    try:
        while True:
            # 读取辅助臂状态
            puppet_obs = puppet.get_observation()
            
            if isinstance(puppet_obs, dict):
                puppet_joints = np.array([
                    puppet_obs.get("shoulder_pan.pos", 0.0),
                    puppet_obs.get("shoulder_lift.pos", 0.0),
                    puppet_obs.get("elbow_flex.pos", 0.0),
                    puppet_obs.get("wrist_flex.pos", 0.0),
                    puppet_obs.get("wrist_roll.pos", 0.0),
                    puppet_obs.get("gripper.pos", 50.0)
                ])
            else:
                puppet_joints = np.zeros(6)
            
            # 发送到主臂
            action = {
                "shoulder_pan.pos": float(puppet_joints[0]),
                "shoulder_lift.pos": float(puppet_joints[1]),
                "elbow_flex.pos": float(puppet_joints[2]),
                "wrist_flex.pos": float(puppet_joints[3]),
                "wrist_roll.pos": float(puppet_joints[4]),
                "gripper.pos": float(puppet_joints[5])
            }
            master.send_action(action)
            
            # 记录数据
            timestamp = time.time() - start_time
            frame_data = {
                "timestamp": timestamp,
                "joints": puppet_joints.tolist(),
                "action": action
            }
            episode_data.append(frame_data)
            
            # 打印状态
            if int(time.time() * 2) % 2 == 0:
                print(f"[INFO] 时间: {timestamp:.1f}s | 数据点: {len(episode_data)}")
            
            time.sleep(0.05)
    
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断，正在保存数据...")
        
        if episode_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = DATA_DIR / f"episode_{episode_id}_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(episode_data, f, indent=2)
            print(f"[OK] 数据已保存: {filename}")
            print(f"[OK] 共收集 {len(episode_data)} 个数据点")
    
    finally:
        print("\n[INFO] 正在断开连接...")
        try:
            master.disconnect()
            print("[OK] 主臂已断开")
        except:
            pass
        
        try:
            puppet.disconnect()
            print("[OK] 辅助臂已断开")
        except:
            pass
        
        print("[OK] 程序已退出")

if __name__ == "__main__":
    teleop_no_home()