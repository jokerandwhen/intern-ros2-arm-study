"""
位置同步脚本：启动时先同步辅助臂和主臂的位置
"""

import time
import numpy as np
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def sync_positions():
    """同步两个机械臂的位置"""
    
    print("="*70)
    print("SoArm101 位置同步脚本")
    print("="*70)
    print("\n这个脚本会：")
    print("  1. 连接两个机械臂")
    print("  2. 读取它们的当前位置")
    print("  3. 将主臂移动到辅助臂的位置（同步）")
    print("  4. 开始远程操控")
    print("="*70)
    
    master = None
    puppet = None
    
    try:
        # 连接主臂
        print("\n[步骤1] 连接主臂（COM3）...")
        master_config = SOFollowerRobotConfig(port="COM3")
        master = SOFollower(master_config)
        master.connect(calibrate=False)
        print("✓ 主臂连接成功")
        
        # 禁用主臂扭矩（可以手动调整）
        print("\n[步骤2] 禁用主臂扭矩...")
        master.bus.disable_torque()
        print("✓ 主臂扭矩已禁用（可以手动移动）")
        
        # 连接辅助臂
        print("\n[步骤3] 连接辅助臂（COM4）...")
        puppet_config = SOFollowerRobotConfig(port="COM4")
        puppet = SOFollower(puppet_config)
        puppet.connect(calibrate=False)
        print("✓ 辅助臂连接成功")
        
        # 禁用辅助臂扭矩（可以手动调整）
        print("\n[步骤4] 禁用辅助臂扭矩...")
        puppet.bus.disable_torque()
        print("✓ 辅助臂扭矩已禁用（可以手动移动）")
        
        # 读取当前位置
        print("\n[步骤5] 读取当前位置...")
        time.sleep(1)
        
        master_pos = master.get_observation()
        puppet_pos = puppet.get_observation()
        
        print("\n主臂当前位置:")
        for joint, pos in master_pos.items():
            print(f"  {joint}: {pos:.2f}")
        
        print("\n辅助臂当前位置:")
        for joint, pos in puppet_pos.items():
            print(f"  {joint}: {pos:.2f}")
        
        # 手动调整提示
        print("\n" + "="*70)
        print("手动调整阶段")
        print("="*70)
        print("请按照以下步骤操作：")
        print("  1. 手动将辅助臂移动到**安全位置**")
        print("  2. 手动将主臂移动到**相同的辅助臂位置**")
        print("  3. 确保两个机械臂位置一致")
        print("  4. 按 Enter 继续...")
        print("="*70)
        
        input("\n按 Enter 继续...")
        
        # 再次读取位置
        print("\n[步骤6] 再次读取位置...")
        puppet_pos = puppet.get_observation()
        
        print("\n辅助臂当前位置（将作为主臂目标）:")
        for joint, pos in puppet_pos.items():
            print(f"  {joint}: {pos:.2f}")
        
        # 启用主臂扭矩
        print("\n[步骤7] 启用主臂扭矩...")
        master.bus.enable_torque()
        print("✓ 主臂扭矩已启用")
        
        # 将主臂移动到辅助臂位置（分步移动）
        print("\n[步骤8] 同步主臂到辅助臂位置...")
        print("⚠️  主臂将缓慢移动到辅助臂位置...")
        time.sleep(2)
        
        # 分步移动（避免突然移动）
        target_pos = np.array([
            puppet_pos.get("shoulder_pan.pos", 0.0),
            puppet_pos.get("shoulder_lift.pos", 0.0),
            puppet_pos.get("elbow_flex.pos", 0.0),
            puppet_pos.get("wrist_flex.pos", 0.0),
            puppet_pos.get("wrist_roll.pos", 0.0),
            puppet_pos.get("gripper.pos", 50.0)
        ])
        
        # 读取主臂当前位置
        current_pos = np.array([
            master_pos.get("shoulder_pan.pos", 0.0),
            master_pos.get("shoulder_lift.pos", 0.0),
            master_pos.get("elbow_flex.pos", 0.0),
            master_pos.get("wrist_flex.pos", 0.0),
            master_pos.get("wrist_roll.pos", 0.0),
            master_pos.get("gripper.pos", 50.0)
        ])
        
        # 分10步移动
        steps = 10
        for i in range(steps):
            interp_pos = current_pos + (target_pos - current_pos) * (i + 1) / steps
            
            action = {
                "shoulder_pan.pos": float(interp_pos[0]),
                "shoulder_lift.pos": float(interp_pos[1]),
                "elbow_flex.pos": float(interp_pos[2]),
                "wrist_flex.pos": float(interp_pos[3]),
                "wrist_roll.pos": float(interp_pos[4]),
                "gripper.pos": float(interp_pos[5])
            }
            
            master.send_action(action)
            print(f"  步骤 {i+1}/{steps}: 移动中...")
            time.sleep(0.5)
        
        print("✓ 主臂已同步到辅助臂位置")
        
        # 开始远程操控
        print("\n" + "="*70)
        print("✓ 位置同步完成，开始远程操控")
        print("="*70)
        print("操作说明：")
        print("  - 辅助臂（COM4）：手动操作（扭矩已禁用）")
        print("  - 主臂（COM3）：自动跟随（扭矩已启用）")
        print("  - 按 Ctrl+C 退出")
        print("="*70 + "\n")
        
        frame = 0
        while True:
            try:
                # 读取辅助臂位置
                puppet_obs = puppet.get_observation()
                
                # 发送到主臂
                action = {
                    "shoulder_pan.pos": puppet_obs.get("shoulder_pan.pos", 0.0),
                    "shoulder_lift.pos": puppet_obs.get("shoulder_lift.pos", 0.0),
                    "elbow_flex.pos": puppet_obs.get("elbow_flex.pos", 0.0),
                    "wrist_flex.pos": puppet_obs.get("wrist_flex.pos", 0.0),
                    "wrist_roll.pos": puppet_obs.get("wrist_roll.pos", 0.0),
                    "gripper.pos": puppet_obs.get("gripper.pos", 50.0)
                }
                master.send_action(action)
                
                frame += 1
                if frame % 20 == 0:
                    print(f"[运行中] 帧: {frame}")
                
                time.sleep(0.05)
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[错误] {e}")
                time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断")
    
    except Exception as e:
        print(f"\n[错误] 程序异常: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n[断开连接]")
        if master:
            try:
                master.disconnect()
            except:
                pass
        if puppet:
            try:
                puppet.disconnect()
            except:
                pass
        print("[OK] 程序已退出")

if __name__ == "__main__":
    sync_positions()