"""
夹爪校准脚本
专门校准辅助臂和主臂的夹爪映射
"""

import json
import time
import numpy as np
from pathlib import Path
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def calibrate_gripper():
    """校准夹爪"""
    
    print("="*70)
    print("SoArm101 夹爪校准脚本")
    print("="*70)
    print("\n夹爪需要单独校准，因为：")
    print("  - 主臂夹爪和辅助臂夹爪的开合范围可能不同")
    print("  - 需要建立精确的开合度映射")
    print("="*70)
    
    master = None
    puppet = None
    gripper_data = []
    
    try:
        # 连接
        print("\n[步骤1] 连接主臂...")
        master_config = SOFollowerRobotConfig(port="COM3")
        master = SOFollower(master_config)
        master.connect(calibrate=False)
        master.bus.disable_torque()
        print("✓ 主臂连接成功")
        
        print("\n[步骤2] 连接辅助臂...")
        puppet_config = SOFollowerRobotConfig(port="COM4")
        puppet = SOFollower(puppet_config)
        puppet.connect(calibrate=False)
        puppet.bus.disable_torque()
        print("✓ 辅助臂连接成功")
        
        # 校准说明
        print("\n" + "="*70)
        print("夹爪校准流程")
        print("="*70)
        print("请按照以下步骤收集5个不同开合度：")
        print("  1. 完全打开（最大开合）")
        print("  2. 打开75%")
        print("  3. 打开50%（半开）")
        print("  4. 打开25%")
        print("  5. 完全关闭（最小开合）")
        print("="*70)
        
        positions = [
            "完全打开（100%）",
            "打开75%",
            "打开50%（半开）",
            "打开25%",
            "完全关闭（0%）"
        ]
        
        for i, pos_name in enumerate(positions):
            print(f"\n[位置 {i+1}/5] {pos_name}")
            print("请手动调整两个夹爪到相同开合度...")
            input("调整完成后按 Enter 记录...")
            
            # 读取夹爪位置（使用原始寄存器值 0-4095）
            # normalize=False 表示不转换为度数，直接返回原始值
            try:
                master_gripper = master.bus.read("Present_Position", "gripper", normalize=False)
                puppet_gripper = puppet.bus.read("Present_Position", "gripper", normalize=False)

                print(f"  主臂夹爪（原始值）: {master_gripper} (0-4095)")
                print(f"  辅助臂夹爪（原始值）: {puppet_gripper} (0-4095)")

                gripper_data.append({
                    "position_name": pos_name,
                    "master_gripper": master_gripper,
                    "puppet_gripper": puppet_gripper,
                    "unit": "raw_register"
                })
            except Exception as e:
                print(f"  [错误] 读取夹爪位置失败: {e}")
                raise
        
        # 分析夹爪数据（使用原始寄存器值）
        print("\n" + "="*70)
        print("夹爪校准数据分析（原始寄存器值：0-4095）")
        print("="*70)
        
        master_values = np.array([d['master_gripper'] for d in gripper_data])
        puppet_values = np.array([d['puppet_gripper'] for d in gripper_data])
        
        print(f"\n主臂夹爪范围: [{master_values.min()}, {master_values.max()}] (原始值)")
        print(f"辅助臂夹爪范围: [{puppet_values.min()}, {puppet_values.max()}] (原始值)")
        
        # 检查是否有足够的变化范围
        master_range = master_values.max() - master_values.min()
        puppet_range = puppet_values.max() - puppet_values.min()
        
        if master_range < 50:
            print(f"\n⚠️ 主臂夹爪变化范围太小（{master_range}），可能无法建立有效映射")
            print("建议检查：")
            print("  1. 主臂夹爪电机连接是否正常")
            print("  2. 手动移动时是否到达极限位置")
        
        if puppet_range < 50:
            print(f"\n⚠️ 辅助臂夹爪变化范围太小（{puppet_range}），可能无法建立有效映射")
        
        # 建立线性映射
        A = np.vstack([puppet_values, np.ones(len(puppet_values))]).T
        slope, intercept = np.linalg.lstsq(A, master_values, rcond=None)[0]
        
        print(f"\n夹爪映射公式: master = {slope:.4f} * puppet + {intercept:.4f}")
        
        # 测试映射
        print("\n映射测试:")
        for i in range(5):
            puppet_val = puppet_values[i]
            master_val = slope * puppet_val + intercept
            print(f"  辅助臂 {puppet_val} → 主臂 {master_val:.1f} (实际: {master_values[i]})")
        
        # 保存夹爪校准数据
        calibration_file = Path("gripper_calibration.json")
        calibration_result = {
            "timestamp": time.time(),
            "slope": slope,
            "intercept": intercept,
            "master_range": [float(master_values.min()), float(master_values.max())],
            "puppet_range": [float(puppet_values.min()), float(puppet_values.max())],
            "data": gripper_data
        }
        
        with open(calibration_file, 'w') as f:
            json.dump(calibration_result, f, indent=2)
        
        print(f"\n✓ 夹爪校准数据已保存: {calibration_file}")
        
        print("\n[OK] 夹爪校准完成！")
        print("现在可以运行 smart_mapping.py 进行远程操控")
    
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
    calibrate_gripper()