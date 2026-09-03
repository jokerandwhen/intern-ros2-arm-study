"""
超安全版本：完全跳过校准，直接连接
"""

import time
import numpy as np
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def ultra_safe_teleop():
    """超安全的远程操控：完全跳过校准"""
    
    print("="*70)
    print("SoArm101 超安全远程操控（跳过所有初始化）")
    print("="*70)
    print("\n⚠️  重要：请确保机械臂已手动移到安全位置！")
    print("   - 所有关节在中间位置")
    print("   - 没有碰撞或卡住")
    print("="*70)
    
    master = None
    puppet = None
    
    try:
        # 连接主臂（跳过校准）
        print("\n[步骤1] 连接主臂（COM3，跳过校准）...")
        master_config = SOFollowerRobotConfig(port="COM3")
        master = SOFollower(master_config)
        master.connect(calibrate=False)  # ← 关键：跳过校准！
        print("✓ 主臂连接成功（无初始化动作）")
        
        # 连接辅助臂（跳过校准）
        print("\n[步骤2] 连接辅助臂（COM4，跳过校准）...")
        puppet_config = SOFollowerRobotConfig(port="COM4")
        puppet = SOFollower(puppet_config)
        puppet.connect(calibrate=False)  # ← 关键：跳过校准！
        print("✓ 辅助臂连接成功（无初始化动作）")
        
        # 测试读取
        print("\n[步骤3] 测试读取辅助臂数据...")
        try:
            puppet_obs = puppet.get_observation()
            print(f"✓ 辅助臂数据: {list(puppet_obs.values())[:3]}...")
        except Exception as e:
            print(f"✗ 读取失败: {e}")
            print("\n请检查辅助臂电源和连接！")
            return
        
        # 测试主臂
        print("\n[步骤4] 测试主臂响应...")
        print("⚠️  即将发送测试动作（保持不动）...")
        time.sleep(2)
        
        test_action = {
            "shoulder_pan.pos": 0.0,
            "shoulder_lift.pos": 0.0,
            "elbow_flex.pos": 0.0,
            "wrist_flex.pos": 0.0,
            "wrist_roll.pos": 0.0,
            "gripper.pos": 50.0
        }
        try:
            master.send_action(test_action)
            print("✓ 主臂测试成功")
        except Exception as e:
            print(f"✗ 主臂响应失败: {e}")
            return
        
        # 开始远程操控
        print("\n" + "="*70)
        print("✓ 开始远程操控")
        print("="*70)
        print("操作说明：")
        print("  1. 手动移动辅助臂（COM4）")
        print("  2. 主臂（COM3）会实时跟随")
        print("  3. 按 Ctrl+C 退出")
        print("="*70 + "\n")
        
        frame = 0
        while True:
            try:
                # 读取辅助臂
                puppet_obs = puppet.get_observation()
                
                if isinstance(puppet_obs, dict):
                    joints = np.array([
                        puppet_obs.get("shoulder_pan.pos", 0.0),
                        puppet_obs.get("shoulder_lift.pos", 0.0),
                        puppet_obs.get("elbow_flex.pos", 0.0),
                        puppet_obs.get("wrist_flex.pos", 0.0),
                        puppet_obs.get("wrist_roll.pos", 0.0),
                        puppet_obs.get("gripper.pos", 50.0)
                    ])
                    
                    # 发送到主臂
                    action = {
                        "shoulder_pan.pos": float(joints[0]),
                        "shoulder_lift.pos": float(joints[1]),
                        "elbow_flex.pos": float(joints[2]),
                        "wrist_flex.pos": float(joints[3]),
                        "wrist_roll.pos": float(joints[4]),
                        "gripper.pos": float(joints[5])
                    }
                    master.send_action(action)
                    
                    frame += 1
                    if frame % 20 == 0:
                        print(f"[运行中] 帧: {frame} | 关节: {joints[:3]}")
                
                time.sleep(0.05)
            
            except Exception as e:
                print(f"[警告] 控制错误: {e}")
                time.sleep(1)
    
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
    ultra_safe_teleop()