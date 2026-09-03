"""
SoArm101 机械臂校准和主从同步程序
功能：
1. 连接两个机械臂（主臂COM3，从臂COM4）
2. 校准两个机械臂（归位到初始位置）
3. 实现主从同步（主臂移动时，从臂实时跟随）
"""

import time
import torch
import numpy as np
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

# ===================== 配置区 =====================
MASTER_PORT = "COM3"   # 主臂串口（你手动控制的臂）
SLAVE_PORT = "COM4"    # 从臂串口（自动跟随的臂）

# 安全参数
JOINT_MIN = -1.0
JOINT_MAX = 1.0
MAX_VELOCITY = 0.3  # 最大速度限制（防止过快移动）

# 归位位置（安全初始位置）
HOME_POSITION = [0.0, -0.3, 0.5, 0.0, 0.0, 0.0]
# ================================================

def clamp_action(action, prev_action=None):
    """动作限幅和速度限制"""
    # 关节限幅
    action = np.clip(action, JOINT_MIN, JOINT_MAX)
    
    # 速度限制
    if prev_action is not None:
        delta = action - prev_action
        delta = np.clip(delta, -MAX_VELOCITY, MAX_VELOCITY)
        action = prev_action + delta
    
    return action

def home_robot(robot, name="Robot"):
    """机械臂归位到安全位置"""
    print(f"[INFO] {name} 正在归位...")
    
    current_pos = np.zeros(6)
    steps = 20  # 分步归位，避免突然运动
    
    for i in range(steps):
        # 渐进移动到归位位置
        target = current_pos + (np.array(HOME_POSITION) - current_pos) * (i + 1) / steps
        target = clamp_action(target, current_pos)
        
        # 构造正确的action字典格式
        action = {
            "shoulder_pan.pos": float(target[0]),
            "shoulder_lift.pos": float(target[1]),
            "elbow_flex.pos": float(target[2]),
            "wrist_flex.pos": float(target[3]),
            "wrist_roll.pos": float(target[4]),
            "gripper.pos": float(target[5])
        }
        
        # 发送动作
        robot.send_action(action)
        
        current_pos = target
        time.sleep(0.1)  # 每步等待100ms
    
    print(f"[OK] {name} 归位完成")

def calibrate_and_sync():
    """主函数：校准和主从同步"""
    
    # 1. 连接主臂（Master）
    print(f"\n[INFO] 正在连接主臂（{MASTER_PORT}）...")
    master_config = SOFollowerRobotConfig(port=MASTER_PORT)
    master = SOFollower(master_config)
    master.connect()
    print("[OK] 主臂连接成功")
    
    # 2. 连接从臂（Slave）
    print(f"\n[INFO] 正在连接从臂（{SLAVE_PORT}）...")
    slave_config = SOFollowerRobotConfig(port=SLAVE_PORT)
    slave = SOFollower(slave_config)
    slave.connect()
    print("[OK] 从臂连接成功")
    
    # 3. 校准两个机械臂（归位）
    print("\n" + "="*50)
    print("开始校准...")
    print("="*50)
    home_robot(master, "主臂")
    home_robot(slave, "从臂")
    print("\n[OK] 校准完成！两个机械臂已归位到安全位置")
    
    # 4. 主从同步模式
    print("\n" + "="*50)
    print("进入主从同步模式")
    print("="*50)
    print("说明：")
    print("  - 主臂（COM3）：你可以手动移动这个臂")
    print("  - 从臂（COM4）：会自动跟随主臂的运动")
    print("  - 按 Ctrl+C 退出程序")
    print("="*50 + "\n")
    
    prev_action = np.array(HOME_POSITION)
    
    try:
            while True:
                # 读取主臂当前状态
                master_obs = master.get_observation()
                
                # 打印完整的观测数据（调试）
                # print(f"[DEBUG] 主臂观测数据: {master_obs}")
                
                # 提取关节角度（前6个值）
                if isinstance(master_obs, dict):
                    # 从字典中提取关节角度
                    master_joints = np.array([
                        master_obs.get("shoulder_pan.pos", 0.0),
                        master_obs.get("shoulder_lift.pos", 0.0),
                        master_obs.get("elbow_flex.pos", 0.0),
                        master_obs.get("wrist_flex.pos", 0.0),
                        master_obs.get("wrist_roll.pos", 0.0),
                        master_obs.get("gripper.pos", 0.0)
                    ])
                elif isinstance(master_obs, np.ndarray):
                    master_joints = master_obs[:6]
                else:
                    master_joints = np.zeros(6)
                
                # 打印原始数据（调试）
                # print(f"[DEBUG] 主臂关节角度: {master_joints}")
                
                # 安全限幅
                master_joints = clamp_action(master_joints, prev_action)
                
                # 发送到从臂（跟随）- 使用字典格式
                action = {
                    "shoulder_pan.pos": float(master_joints[0]),
                    "shoulder_lift.pos": float(master_joints[1]),
                    "elbow_flex.pos": float(master_joints[2]),
                    "wrist_flex.pos": float(master_joints[3]),
                    "wrist_roll.pos": float(master_joints[4]),
                    "gripper.pos": float(master_joints[5])
                }
                slave.send_action(action)
                
                # 更新历史
                prev_action = master_joints.copy()
                
                # 打印状态（每秒打印一次）
                if int(time.time()) % 1 == 0:
                    print(f"[INFO] 主臂状态: {master_joints[:3]}... | 从臂跟随中...")
                
                time.sleep(0.05)  # 20Hz控制频率
    
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断，正在退出...")
    
    finally:
        # 退出前归位
        print("\n[INFO] 正在归位机械臂...")
        home_robot(master, "主臂")
        home_robot(slave, "从臂")
        
        # 断开连接
        master.disconnect()
        slave.disconnect()
        print("\n[OK] 程序已退出，机械臂已归位")

if __name__ == "__main__":
    calibrate_and_sync()