"""
SoArm101 远程操控 + 数据收集程序
功能：
1. 用户操作辅助臂（COM4）远程控制主臂（COM3）
2. 实时记录辅助臂的动作用于数据集收集
3. 保存数据到CSV文件
"""

import time
import numpy as np
import json
from datetime import datetime
from pathlib import Path
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

# ===================== 配置区 =====================
MASTER_ARM_PORT = "COM3"   # 主臂（执行任务的臂）
PUPPET_ARM_PORT = "COM4"   # 辅助臂（用户操作的臂，用于数据收集）

# 数据保存路径
DATA_DIR = Path("dataset")
DATA_DIR.mkdir(exist_ok=True)

# 安全参数
JOINT_MIN = -1.0
JOINT_MAX = 1.0
MAX_VELOCITY = 0.3

# 归位位置
HOME_POSITION = [0.0, -0.3, 0.5, 0.0, 0.0, 0.0]
# ================================================

def clamp_action(action, prev_action=None):
    """动作限幅和速度限制"""
    action = np.clip(action, JOINT_MIN, JOINT_MAX)
    if prev_action is not None:
        delta = action - prev_action
        delta = np.clip(delta, -MAX_VELOCITY, MAX_VELOCITY)
        action = prev_action + delta
    return action

def home_robot(robot, name="Robot"):
    """机械臂归位"""
    print(f"[INFO] {name} 正在归位...")
    
    # 归位位置（度数值）
    # shoulder: 0度（中间）
    # shoulder_lift: 0度（水平）
    # elbow_flex: 30度（轻微弯曲）
    # wrist: 0度（中间）
    # gripper: 50度（半开）
    home_degrees = [0.0, 0.0, 30.0, 0.0, 0.0, 50.0]
    
    current_pos = np.zeros(6)
    steps = 20  # 分步归位，避免突然运动
    
    for i in range(steps):
        # 渐进移动到归位位置
        target = current_pos + (np.array(home_degrees) - current_pos) * (i + 1) / steps
        
        # 构造正确的action字典格式（度数值）
        action = {
            "shoulder_pan.pos": float(target[0]),
            "shoulder_lift.pos": float(target[1]),
            "elbow_flex.pos": float(target[2]),
            "wrist_flex.pos": float(target[3]),
            "wrist_roll.pos": float(target[4]),
            "gripper.pos": float(target[5])
        }
        robot.send_action(action)
        
        current_pos = target
        time.sleep(0.1)  # 每步等待100ms
    
    print(f"[OK] {name} 归位完成")

def save_episode(data, episode_id):
    """保存一个episode的数据"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = DATA_DIR / f"episode_{episode_id}_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"[OK] 数据已保存: {filename}")
    return filename

def teleop_and_collect():
    """远程操控 + 数据收集主函数"""
    
    # 1. 连接主臂（执行任务）
    print(f"\n[INFO] 正在连接主臂（{MASTER_ARM_PORT}）...")
    master_config = SOFollowerRobotConfig(port=MASTER_ARM_PORT)
    master = SOFollower(master_config)
    master.connect()
    print("[OK] 主臂连接成功")
    
    # 2. 连接辅助臂（用户操作）
    print(f"\n[INFO] 正在连接辅助臂（{PUPPET_ARM_PORT}）...")
    puppet_config = SOFollowerRobotConfig(port=PUPPET_ARM_PORT)
    puppet = SOFollower(puppet_config)
    puppet.connect()
    print("[OK] 辅助臂连接成功")
    
    # 3. 归位两个机械臂
    print("\n" + "="*50)
    print("开始归位...")
    print("="*50)
    home_robot(master, "主臂")
    home_robot(puppet, "辅助臂")
    print("\n[OK] 归位完成！")
    
    # 4. 远程操控模式
    print("\n" + "="*50)
    print("远程操控 + 数据收集模式")
    print("="*50)
    print("说明：")
    print("  - 辅助臂（COM4）：你手动操作这个臂")
    print("  - 主臂（COM3）：会自动跟随辅助臂的运动")
    print("  - 数据会自动记录用于训练")
    print("  - 按 Ctrl+C 停止当前episode并保存数据")
    print("  - 再次运行开始新的episode")
    print("="*50 + "\n")
    
    # 数据收集
    episode_id = 1
    episode_data = []
    prev_action = np.array(HOME_POSITION)
    start_time = time.time()
    
    try:
        while True:
            # 读取辅助臂（用户操作的）当前状态
            puppet_obs = puppet.get_observation()
            
            # 提取关节角度（度数值，不需要归一化）
            if isinstance(puppet_obs, dict):
                # 直接使用度数值（lerobot期望度数值）
                puppet_joints = np.array([
                    puppet_obs.get("shoulder_pan.pos", 0.0),  # 度数值
                    puppet_obs.get("shoulder_lift.pos", 0.0),
                    puppet_obs.get("elbow_flex.pos", 0.0),
                    puppet_obs.get("wrist_flex.pos", 0.0),
                    puppet_obs.get("wrist_roll.pos", 0.0),
                    puppet_obs.get("gripper.pos", 50.0)  # 默认半开
                ])
            else:
                puppet_joints = np.zeros(6)
            
            # 发送到主臂（跟随辅助臂）- 使用度数值
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
            
            # 更新历史
            prev_action = puppet_joints.copy()
            
            # 打印状态
            if int(time.time() * 2) % 2 == 0:
                print(f"[INFO] 时间: {timestamp:.1f}s | 关节: {puppet_joints[:3]}... | 数据点: {len(episode_data)}")
            
            time.sleep(0.05)  # 20Hz控制频率
    
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断，正在保存数据...")
        
        # 保存episode数据
        if episode_data:
            filename = save_episode(episode_data, episode_id)
            print(f"[OK] Episode {episode_id} 完成，共 {len(episode_data)} 个数据点")
            episode_id += 1
    
    finally:
        # 断开连接（不归位，避免过载）
        print("\n[INFO] 正在断开连接...")
        
        try:
            master.disconnect()
            print("[OK] 主臂已断开")
        except Exception as e:
            print(f"[WARN] 主臂断开失败（可能已过载）: {e}")
        
        try:
            puppet.disconnect()
            print("[OK] 辅助臂已断开")
        except Exception as e:
            print(f"[WARN] 辅助臂断开失败（可能已过载）: {e}")
        
        print("\n[OK] 程序已退出")
        print(f"[INFO] 数据保存在: {DATA_DIR}")
        print(f"[INFO] 共收集 {len(episode_data)} 个数据点")

if __name__ == "__main__":
    teleop_and_collect()