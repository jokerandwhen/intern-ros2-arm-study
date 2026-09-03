"""
终极解决方案：直接禁用扭矩，手动控制
"""

import time
import numpy as np
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def test_torque_control():
    """测试扭矩控制"""
    
    print("="*70)
    print("SoArm101 扭矩控制测试")
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
        
        # 立即禁用扭矩
        print("\n[步骤2] 禁用主臂扭矩（可以手动移动）...")
        try:
            master.bus.disable_torque()
            print("✓ 主臂扭矩已禁用，现在可以手动移动主臂")
        except Exception as e:
            print(f"⚠ 禁用主臂扭矩失败: {e}")
        
        # 连接辅助臂
        print("\n[步骤3] 连接辅助臂（COM4）...")
        puppet_config = SOFollowerRobotConfig(port="COM4")
        puppet = SOFollower(puppet_config)
        puppet.connect(calibrate=False)
        print("✓ 辅助臂连接成功")
        
        # 立即禁用扭矩
        print("\n[步骤4] 禁用辅助臂扭矩（可以手动移动）...")
        try:
            puppet.bus.disable_torque()
            print("✓ 辅助臂扭矩已禁用，现在可以手动移动辅助臂")
        except Exception as e:
            print(f"⚠ 禁用辅助臂扭矩失败: {e}")
        
        # 测试读取位置
        print("\n[步骤5] 测试读取位置...")
        time.sleep(1)
        
        try:
            puppet_pos = puppet.get_observation()
            print(f"✓ 辅助臂位置: {puppet_pos}")
        except Exception as e:
            print(f"✗ 读取辅助臂位置失败: {e}")
        
        try:
            master_pos = master.get_observation()
            print(f"✓ 主臂位置: {master_pos}")
        except Exception as e:
            print(f"✗ 读取主臂位置失败: {e}")
        
        # 测试手动控制
        print("\n" + "="*70)
        print("手动测试")
        print("="*70)
        print("现在两个机械臂的扭矩都已禁用，你可以：")
        print("  1. 手动移动辅助臂")
        print("  2. 手动移动主臂")
        print("  3. 观察3秒...")
        print("="*70)
        
        for i in range(3):
            print(f"  {3-i}秒...")
            time.sleep(1)
        
        # 启用扭矩并测试控制
        print("\n[步骤6] 启用主臂扭矩...")
        try:
            master.bus.enable_torque()
            print("✓ 主臂扭矩已启用")
        except Exception as e:
            print(f"⚠ 启用主臂扭矩失败: {e}")
        
        print("\n[步骤7] 发送测试动作到主臂...")
        print("⚠️  主臂即将轻微移动（保持不动）...")
        time.sleep(2)
        
        # 读取当前位置
        current_pos = master.get_observation()
        
        # 发送当前位置（不移动）
        action = {
            "shoulder_pan.pos": current_pos.get("shoulder_pan.pos", 0.0),
            "shoulder_lift.pos": current_pos.get("shoulder_lift.pos", 0.0),
            "elbow_flex.pos": current_pos.get("elbow_flex.pos", 0.0),
            "wrist_flex.pos": current_pos.get("wrist_flex.pos", 0.0),
            "wrist_roll.pos": current_pos.get("wrist_roll.pos", 0.0),
            "gripper.pos": current_pos.get("gripper.pos", 50.0)
        }
        
        try:
            master.send_action(action)
            print("✓ 主臂动作已发送（保持当前位置，不移动）")
        except Exception as e:
            print(f"✗ 发送动作失败: {e}")
        
        # 进入手动控制模式
        print("\n" + "="*70)
        print("手动控制模式")
        print("="*70)
        print("说明：")
        print("  - 辅助臂扭矩已禁用，你可以手动移动它")
        print("  - 主臂扭矩已启用，会跟随辅助臂")
        print("  - 按 Ctrl+C 退出")
        print("="*70 + "\n")
        
        while True:
            try:
                # 读取辅助臂位置
                puppet_pos = puppet.get_observation()
                
                # 发送到主臂
                action = {
                    "shoulder_pan.pos": puppet_pos.get("shoulder_pan.pos", 0.0),
                    "shoulder_lift.pos": puppet_pos.get("shoulder_lift.pos", 0.0),
                    "elbow_flex.pos": puppet_pos.get("elbow_flex.pos", 0.0),
                    "wrist_flex.pos": puppet_pos.get("wrist_flex.pos", 0.0),
                    "wrist_roll.pos": puppet_pos.get("wrist_roll.pos", 0.0),
                    "gripper.pos": puppet_pos.get("gripper.pos", 50.0)
                }
                master.send_action(action)
                
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
    test_torque_control()