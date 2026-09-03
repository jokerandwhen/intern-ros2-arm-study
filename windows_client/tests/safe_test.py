"""
最简单的远程操控测试版本
- 完全跳过归位
- 添加详细错误处理
- 逐个测试功能
"""

import time
import numpy as np
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def safe_teleop():
    """安全的远程操控测试"""
    
    print("="*60)
    print("SoArm101 远程操控测试（安全模式）")
    print("="*60)
    
    master = None
    puppet = None
    
    try:
        # 步骤1：连接主臂
        print("\n[步骤1] 连接主臂（COM3）...")
        master_config = SOFollowerRobotConfig(port="COM3")
        master = SOFollower(master_config)
        master.connect()
        print("✓ 主臂连接成功（不归位）")
        
        # 步骤2：连接辅助臂
        print("\n[步骤2] 连接辅助臂（COM4）...")
        puppet_config = SOFollowerRobotConfig(port="COM4")
        puppet = SOFollower(puppet_config)
        puppet.connect()
        print("✓ 辅助臂连接成功（不归位）")
        
        # 步骤3：测试读取辅助臂数据
        print("\n[步骤3] 测试读取辅助臂数据...")
        for i in range(3):
            try:
                puppet_obs = puppet.get_observation()
                print(f"✓ 第{i+1}次读取成功: {puppet_obs}")
            except Exception as e:
                print(f"✗ 第{i+1}次读取失败: {e}")
                if i == 2:
                    print("\n[错误] 辅助臂无法读取数据，请检查：")
                    print("  1. 辅助臂电源是否连接？")
                    print("  2. 辅助臂是否过载？（红灯闪烁）")
                    print("  3. 串口COM4是否正确？")
                    return
            time.sleep(0.5)
        
        # 步骤4：测试主臂响应
        print("\n[步骤4] 测试主臂响应...")
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
            print("✓ 主臂响应测试成功")
        except Exception as e:
            print(f"✗ 主臂响应失败: {e}")
            return
        
        # 步骤5：进入远程操控模式
        print("\n" + "="*60)
        print("开始远程操控")
        print("="*60)
        print("说明：")
        print("  - 移动辅助臂（COM4），主臂（COM3）会跟随")
        print("  - 按 Ctrl+C 退出")
        print("="*60 + "\n")
        
        frame_count = 0
        start_time = time.time()
        
        while True:
            try:
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
                    
                    frame_count += 1
                    
                    # 每20帧打印一次状态
                    if frame_count % 20 == 0:
                        elapsed = time.time() - start_time
                        print(f"[运行中] 时间: {elapsed:.1f}s | 帧数: {frame_count} | 关节: {puppet_joints[:3]}...")
                
                time.sleep(0.05)  # 20Hz
                
            except Exception as e:
                print(f"[错误] 控制循环出错: {e}")
                print("[INFO] 3秒后重试...")
                time.sleep(3)
    
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断")
    
    except Exception as e:
        print(f"\n[错误] 程序异常: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 安全断开
        print("\n" + "="*60)
        print("断开连接")
        print("="*60)
        
        if master:
            try:
                master.disconnect()
                print("✓ 主臂已断开")
            except:
                print("⚠ 主臂断开时出现警告（可能已过载）")
        
        if puppet:
            try:
                puppet.disconnect()
                print("✓ 辅助臂已断开")
            except:
                print("⚠ 辅助臂断开时出现警告（可能已过载）")
        
        print("\n[OK] 程序已退出")

if __name__ == "__main__":
    safe_teleop()