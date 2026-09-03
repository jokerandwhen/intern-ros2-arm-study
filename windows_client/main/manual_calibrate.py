"""
手动校准脚本：通过多个位置建立精确映射
"""

import json
import time
import numpy as np
from pathlib import Path
from datetime import datetime
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

# 配置
CALIBRATION_FILE = Path("calibration_data.json")

def manual_calibration():
    """手动校准：持续收集位置建立映射"""

    print("="*70)
    print("SoArm101 手动校准脚本（持续收集模式）")
    print("="*70)
    print("\n将持续收集位置数据，按 Ctrl+C 停止")
    print("建议收集10-15个不同位置以获得最佳映射效果")
    print("="*70)
    
    master = None
    puppet = None
    calibration_data = []
    
    try:
        # 连接机械臂
        print("\n[步骤1] 连接主臂（COM3）...")
        master_config = SOFollowerRobotConfig(port="COM3")
        master = SOFollower(master_config)
        master.connect(calibrate=False)
        master.bus.disable_torque()  # 禁用扭矩，可以手动移动
        print("✓ 主臂连接成功（扭矩已禁用）")
        
        print("\n[步骤2] 连接辅助臂（COM4）...")
        puppet_config = SOFollowerRobotConfig(port="COM4")
        puppet = SOFollower(puppet_config)
        puppet.connect(calibrate=False)
        puppet.bus.disable_torque()  # 禁用扭矩，可以手动移动
        print("✓ 辅助臂连接成功（扭矩已禁用）")
        
        # 校准说明
        print("\n" + "="*70)
        print("校准流程")
        print("="*70)
        print("持续收集模式：")
        print("  1. 手动调整两个机械臂到相同位置")
        print("  2. 确保位置完全一致")
        print("  3. 按 Enter 记录当前位置")
        print("  4. 重复步骤1-3，收集不同位置")
        print("  5. 按 Ctrl+C 停止收集")
        print("="*70)

        # 收集位置数据（无限循环）
        sample_count = 0
        while True:
            sample_count += 1
            print(f"\n[位置 {sample_count}]")
            print("请手动调整两个机械臂到相同位置...")
            input("调整完成后按 Enter 记录...")

            # 读取位置
            master_pos = master.get_observation()
            puppet_pos = puppet.get_observation()

            # 夹爪使用原始寄存器值（覆盖度数值）
            try:
                master_pos["gripper.pos"] = master.bus.read("Present_Position", "gripper", normalize=False)
                puppet_pos["gripper.pos"] = puppet.bus.read("Present_Position", "gripper", normalize=False)
            except Exception as e:
                print(f"  ⚠️ 读取夹爪原始位置失败: {e}")

            print("\n主臂位置:")
            for joint, pos in master_pos.items():
                if joint == "gripper.pos":
                    print(f"  {joint}: {pos} (原始值 0-4095)")
                else:
                    print(f"  {joint}: {pos:.2f}")

            print("\n辅助臂位置:")
            for joint, pos in puppet_pos.items():
                if joint == "gripper.pos":
                    print(f"  {joint}: {pos} (原始值 0-4095)")
                else:
                    print(f"  {joint}: {pos:.2f}")
            
            # 记录数据
            position_data = {
                "sample_id": sample_count,
                "timestamp": time.time(),
                "master": master_pos,
                "puppet": puppet_pos
            }
            calibration_data.append(position_data)

            print(f"✓ 位置 {sample_count} 已记录（共 {len(calibration_data)} 个）")
        
        # 保存校准数据
        print("\n" + "="*70)
        print("保存校准数据")
        print("="*70)
        
        calibration_result = {
            "timestamp": datetime.now().isoformat(),
            "num_samples": len(calibration_data),
            "data": calibration_data
        }
        
        with open(CALIBRATION_FILE, 'w') as f:
            json.dump(calibration_result, f, indent=2)
        
        print(f"✓ 校准数据已保存: {CALIBRATION_FILE}")
        print(f"✓ 共收集 {len(calibration_data)} 个位置")
        
        # 分析校准数据
        print("\n" + "="*70)
        print("校准数据分析")
        print("="*70)
        
        # 计算平均值和标准差
        joints = ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos", 
                  "wrist_flex.pos", "wrist_roll.pos", "gripper.pos"]
        
        for joint in joints:
            master_values = [d["master"].get(joint, 0) for d in calibration_data]
            puppet_values = [d["puppet"].get(joint, 0) for d in calibration_data]
            
            # 计算差异
            diff = np.array(master_values) - np.array(puppet_values)
            mean_diff = np.mean(diff)
            std_diff = np.std(diff)
            
            print(f"\n{joint}:")
            print(f"  主臂范围: [{min(master_values):.2f}, {max(master_values):.2f}]")
            print(f"  辅助臂范围: [{min(puppet_values):.2f}, {max(puppet_values):.2f}]")
            print(f"  平均差异: {mean_diff:.2f} ± {std_diff:.2f}")
        
        # 测试校准效果
        print("\n" + "="*70)
        print("测试校准效果")
        print("="*70)
        print("即将启用主臂扭矩，测试远程操控...")
        time.sleep(2)
        
        # 启用主臂扭矩
        master.bus.enable_torque()
        print("✓ 主臂扭矩已启用")
        
        # 测试：读取辅助臂位置并发送到主臂
        print("\n测试远程操控（按 Ctrl+C 停止）...")
        frame = 0
        while True:
            try:
                puppet_obs = puppet.get_observation()
                
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
                    print(f"[测试中] 帧: {frame}")
                
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
    manual_calibration()