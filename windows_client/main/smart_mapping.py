"""
基于校准数据的智能映射脚本
使用线性回归将辅助臂位置转换到主臂位置
"""

import json
import time
import numpy as np
from pathlib import Path
from scipy import interpolate
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

# 配置
CALIBRATION_FILE = Path("calibration_data.json")
GRIPPER_CALIBRATION_FILE = Path("gripper_calibration.json")

def load_calibration_data():
    """加载校准数据"""
    if not CALIBRATION_FILE.exists():
        raise FileNotFoundError(f"校准文件不存在: {CALIBRATION_FILE}")

    with open(CALIBRATION_FILE, 'r') as f:
        data = json.load(f)

    return data['data']

def load_gripper_calibration():
    """加载夹爪校准数据"""
    if not GRIPPER_CALIBRATION_FILE.exists():
        print(f"⚠️ 夹爪校准文件不存在: {GRIPPER_CALIBRATION_FILE}")
        print("  将使用默认映射（1:1）")
        return None

    with open(GRIPPER_CALIBRATION_FILE, 'r') as f:
        data = json.load(f)

    return data

def build_mapping_functions(calibration_data):
    """建立映射函数（辅助臂 → 主臂）"""
    
    joints = ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos", 
              "wrist_flex.pos", "wrist_roll.pos", "gripper.pos"]
    
    mapping_functions = {}
    
    for joint in joints:
        # 提取该关节的所有数据点
        puppet_values = np.array([d['puppet'].get(joint, 0) for d in calibration_data])
        master_values = np.array([d['master'].get(joint, 0) for d in calibration_data])
        
        # 建立线性映射（简单但有效）
        # master = a * puppet + b
        # 使用最小二乘法
        A = np.vstack([puppet_values, np.ones(len(puppet_values))]).T
        slope, intercept = np.linalg.lstsq(A, master_values, rcond=None)[0]
        
        mapping_functions[joint] = {
            'slope': slope,
            'intercept': intercept,
            'puppet_min': float(puppet_values.min()),
            'puppet_max': float(puppet_values.max())
        }
        
        print(f"{joint}:")
        print(f"  映射公式: master = {slope:.4f} * puppet + {intercept:.4f}")
        print(f"  辅助臂范围: [{puppet_values.min():.2f}, {puppet_values.max():.2f}]")
        print(f"  主臂范围: [{master_values.min():.2f}, {master_values.max():.2f}]")
    
    return mapping_functions

def puppet_to_master(puppet_pos, mapping_functions, gripper_calibration=None):
    """将辅助臂位置转换到主臂位置

    Args:
        puppet_pos: 辅助臂位置字典
        mapping_functions: 关节映射函数字典
        gripper_calibration: 夹爪校准数据（可选）
    """

    master_pos = {}

    for joint, params in mapping_functions.items():
        puppet_val = puppet_pos.get(joint, 0)

        # 应用线性映射
        master_val = params['slope'] * puppet_val + params['intercept']

        # 特殊处理：夹爪映射（使用专用校准数据）
        if joint == "gripper.pos":
            if gripper_calibration:
                # 使用夹爪校准公式：master = slope * puppet + intercept
                slope = gripper_calibration.get('slope', 1.0)
                intercept = gripper_calibration.get('intercept', 0.0)
                master_val = slope * puppet_val + intercept

                # 限制在合理范围内
                puppet_range = gripper_calibration.get('puppet_range', [0, 4095])
                master_range = gripper_calibration.get('master_range', [0, 4095])
                master_val = np.clip(master_val, master_range[0], master_range[1])
            else:
                # 如果没有夹爪校准数据，使用默认映射
                master_val = puppet_val
                master_val = np.clip(master_val, 0, 100)

        # ⚠️ shoulder_lift 方向反转修复
        # 问题：辅助臂向上 → 主臂向下（方向相反）
        # 解决：强制反转 shoulder_lift 的映射值
        if joint == "shoulder_lift.pos":
            # 原始映射（方向反转）：master = slope * puppet + intercept
            # 修复后（方向正确）：master = -slope * puppet + intercept（反转）
            master_val = -params['slope'] * puppet_val + params['intercept']
            # 注意：这里使用了 -slope 来反转方向
        
        # 应用安全限幅（根据主臂的物理范围）
        if joint == "shoulder_lift.pos":
            # shoulder_lift范围：-169.80到155.47
            master_val = np.clip(master_val, -160, 150)
        elif joint == "shoulder_pan.pos":
            # shoulder_pan范围：-41.54到171.91
            master_val = np.clip(master_val, -40, 170)
        elif joint in ["elbow_flex.pos", "wrist_flex.pos"]:
            # 肘部和腕部限制在±100度
            master_val = np.clip(master_val, -100, 100)
        elif joint == "wrist_roll.pos":
            # 腕部旋转限制在±90度
            master_val = np.clip(master_val, -90, 90)
        
        master_pos[joint] = float(master_val)
    
    return master_pos

def smart_teleop():
    """智能远程操控（基于校准映射）"""
    
    print("="*70)
    print("SoArm101 智能远程操控（基于校准映射）")
    print("="*70)
    
    # 加载校准数据
    print("\n[步骤1] 加载校准数据...")
    calibration_data = load_calibration_data()
    print(f"✓ 已加载 {len(calibration_data)} 个校准位置")

    # 加载夹爪校准数据
    print("\n[步骤2] 加载夹爪校准数据...")
    gripper_calibration = load_gripper_calibration()
    if gripper_calibration:
        print(f"✓ 已加载夹爪校准数据")
        print(f"  主臂夹爪范围: {gripper_calibration['master_range']}")
        print(f"  辅助臂夹爪范围: {gripper_calibration['puppet_range']}")
        print(f"  映射公式: master = {gripper_calibration['slope']:.4f} * puppet + {gripper_calibration['intercept']:.4f}")
    else:
        print("  将使用默认夹爪映射（1:1）")

    # 建立映射函数
    print("\n[步骤3] 建立映射函数...")
    mapping_functions = build_mapping_functions(calibration_data)
    print("\n✓ 映射函数已建立")
    
    master = None
    puppet = None
    
    try:
        # 连接机械臂
        print("\n[步骤4] 连接主臂（COM3）...")
        master_config = SOFollowerRobotConfig(port="COM3")
        master = SOFollower(master_config)
        master.connect(calibrate=False)
        master.bus.disable_torque()
        print("✓ 主臂连接成功（扭矩已禁用）")

        print("\n[步骤5] 连接辅助臂（COM4）...")
        puppet_config = SOFollowerRobotConfig(port="COM4")
        puppet = SOFollower(puppet_config)
        puppet.connect(calibrate=False)
        puppet.bus.disable_torque()
        print("✓ 辅助臂连接成功（扭矩已禁用）")

        # 读取初始位置
        print("\n[步骤6] 读取初始位置...")
        master_init = master.get_observation()
        puppet_init = puppet.get_observation()

        # 夹爪使用原始值（覆盖度数值）
        try:
            master_init["gripper.pos"] = master.bus.read("Present_Position", "gripper", normalize=False)
            puppet_init["gripper.pos"] = puppet.bus.read("Present_Position", "gripper", normalize=False)
            print("  夹爪位置已使用原始寄存器值（0-4095）")
        except Exception as e:
            print(f"  ⚠️ 读取夹爪原始位置失败: {e}")

        print("\n主臂初始位置:")
        for joint, pos in list(master_init.items())[:3]:
            print(f"  {joint}: {pos:.2f}")

        print("\n辅助臂初始位置:")
        for joint, pos in list(puppet_init.items())[:3]:
            print(f"  {joint}: {pos:.2f}")
        
        # 计算映射后的主臂位置
        print("\n[步骤7] 计算映射位置...")
        master_target = puppet_to_master(puppet_init, mapping_functions, gripper_calibration)
        
        print("\n映射后的主臂目标位置:")
        for joint, pos in list(master_target.items())[:3]:
            print(f"  {joint}: {pos:.2f}")
        
        # 安全初始化：渐进移动主臂到目标位置
        print("\n" + "="*70)
        print("安全初始化阶段")
        print("="*70)
        print("程序将渐进移动主臂到安全位置，避免舵机过载...")
        print("如果主臂位置异常，请手动调整后再继续")
        print("="*70)

        input("\n按 Enter 开始安全初始化...")

        # 读取主臂当前位置
        print("\n[步骤6.1] 读取主臂当前位置...")
        master_current = master.get_observation()
        print(f"  主臂当前位置: shoulder_lift = {master_current['shoulder_lift.pos']:.2f}°")

        # 计算安全的目标位置（使用主臂当前位置，避免跳跃）
        safe_target = {
            "shoulder_pan.pos": master_current.get("shoulder_pan.pos", 0.0),
            "shoulder_lift.pos": master_current.get("shoulder_lift.pos", 0.0),
            "elbow_flex.pos": master_current.get("elbow_flex.pos", 0.0),
            "wrist_flex.pos": master_current.get("wrist_flex.pos", 0.0),
            "wrist_roll.pos": master_current.get("wrist_roll.pos", 0.0),
            "gripper.pos": 50.0
        }

        print(f"  安全目标位置: shoulder_lift = {safe_target['shoulder_lift.pos']:.2f}°")

        # 渐进移动到安全位置
        print("\n[步骤6.2] 渐进移动主臂到安全位置...")
        steps = 10
        for i in range(steps):
            progress = (i + 1) / steps
            target = {
                "shoulder_pan.pos": float(safe_target["shoulder_pan.pos"] * progress),
                "shoulder_lift.pos": float(safe_target["shoulder_lift.pos"] * progress),
                "elbow_flex.pos": float(safe_target["elbow_flex.pos"] * progress),
                "wrist_flex.pos": float(safe_target["wrist_flex.pos"] * progress),
                "wrist_roll.pos": float(safe_target["wrist_roll.pos"] * progress),
                "gripper.pos": 50.0
            }
            master.send_action(target)
            time.sleep(0.1)

        print("✓ 主臂已移动到安全位置")

        # 手动调整提示
        print("\n" + "="*70)
        print("手动调整阶段")
        print("="*70)
        print("请按照以下步骤操作：")
        print("  1. 手动将辅助臂移动到**中间位置**")
        print("  2. 手动将主臂移动到**中间位置**（与辅助臂位置对应）")
        print("  3. 确保两个机械臂在安全位置")
        print("  4. 按 Enter 开始测试...")
        print("="*70)

        input("\n按 Enter 继续...")

        # 启用主臂扭矩
        print("\n[步骤8] 启用主臂扭矩...")
        master.bus.enable_torque()
        print("✓ 主臂扭矩已启用")

        # 测试映射效果
        print("\n[步骤9] 测试映射效果...")
        print("现在可以移动辅助臂，主臂会根据映射跟随...")
        print("按 Ctrl+C 停止")
        print("="*70 + "\n")
        
        frame = 0
        while True:
            try:
                # 读取辅助臂位置
                puppet_pos = puppet.get_observation()

                # 夹爪使用原始值读取（覆盖度数值）
                try:
                    puppet_gripper_raw = puppet.bus.read("Present_Position", "gripper", normalize=False)
                    puppet_pos["gripper.pos"] = puppet_gripper_raw
                except:
                    pass  # 如果读取失败，保留原有值

                # 映射到主臂位置
                master_pos = puppet_to_master(puppet_pos, mapping_functions, gripper_calibration)

                # 发送到主臂（其他关节）
                action = {
                    "shoulder_pan.pos": master_pos.get("shoulder_pan.pos", 0.0),
                    "shoulder_lift.pos": master_pos.get("shoulder_lift.pos", 0.0),
                    "elbow_flex.pos": master_pos.get("elbow_flex.pos", 0.0),
                    "wrist_flex.pos": master_pos.get("wrist_flex.pos", 0.0),
                    "wrist_roll.pos": master_pos.get("wrist_roll.pos", 0.0),
                }
                master.send_action(action)

                # 夹爪单独控制（使用原始寄存器值）
                gripper_value = int(master_pos.get("gripper.pos", 2048))
                try:
                    master.bus.sync_write("Goal_Position", {"gripper": gripper_value}, normalize=False)
                except Exception as e_gripper:
                    # 如果sync_write失败，尝试使用send_action
                    try:
                        master.send_action({"gripper.pos": float(gripper_value)})
                    except Exception as e_action:
                        pass  # 忽略夹爪控制错误
                
                frame += 1
                if frame % 20 == 0:
                    puppet_vals = [puppet_pos.get(j, 0) for j in list(mapping_functions.keys())[:3]]
                    master_vals = [master_pos.get(j, 0) for j in list(mapping_functions.keys())[:3]]
                    print(f"[帧{frame}] 辅助臂: {puppet_vals} → 主臂: {master_vals}")
                
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
    smart_teleop()