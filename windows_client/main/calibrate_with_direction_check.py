"""
SoArm101 校准程序（带方向同步检查）
功能：
1. 连接主臂（COM3）和辅助臂（COM4）
2. 检测两个臂的移动方向是否一致
3. 如果方向不一致，提示用户调整
4. 记录校准数据到 calibration_data.json
"""

import json
import time
import numpy as np
from datetime import datetime
from pathlib import Path
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

# 配置
MASTER_PORT = "COM3"
PUPPET_PORT = "COM4"
CALIBRATION_FILE = Path("calibration_data.json")
NUM_SAMPLES = 15  # 增加样本数量

def get_joint_dict(observation):
    """从观测数据中提取关节角度字典"""
    if isinstance(observation, dict):
        return observation
    else:
        # 如果是数组，转换为字典
        joints = ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos", 
                  "wrist_flex.pos", "wrist_roll.pos", "gripper.pos"]
        return {joints[i]: float(observation[i]) for i in range(min(6, len(observation)))}

def normalize_angle_diff(diff):
    """归一化角度差，处理跨越 ±180° 边界的情况"""
    while diff > 180:
        diff -= 360
    while diff < -180:
        diff += 360
    return diff

def check_direction_consistency(master_start, master_end, puppet_start, puppet_end):
    """检查主臂和辅助臂的移动方向是否一致"""

    joints = ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos",
              "wrist_flex.pos", "wrist_roll.pos"]

    issues = []

    for joint in joints:
        # 计算原始角度差
        master_delta_raw = master_end.get(joint, 0) - master_start.get(joint, 0)
        puppet_delta_raw = puppet_end.get(joint, 0) - puppet_start.get(joint, 0)

        # 归一化角度差（处理 ±180° 跨越问题）
        master_delta = normalize_angle_diff(master_delta_raw)
        puppet_delta = normalize_angle_diff(puppet_delta_raw)

        # 如果两个臂移动方向相反（符号不同）
        if master_delta * puppet_delta < 0 and abs(master_delta) > 5 and abs(puppet_delta) > 5:
            issues.append({
                'joint': joint,
                'master_delta': master_delta,
                'puppet_delta': puppet_delta,
                'master_delta_raw': master_delta_raw,
                'puppet_delta_raw': puppet_delta_raw
            })

    return issues

def calibrate_with_direction_check():
    """主校准函数（带方向检查）"""
    
    print("="*70)
    print("SoArm101 校准程序（带方向同步检查）")
    print("="*70)
    
    master = None
    puppet = None
    calibration_data = []
    
    try:
        # 1. 连接主臂
        print("\n[步骤1] 连接主臂（COM3）...")
        master_config = SOFollowerRobotConfig(port=MASTER_PORT)
        master = SOFollower(master_config)
        master.connect(calibrate=False)
        master.bus.disable_torque()
        print("✓ 主臂连接成功（扭矩已禁用）")
        
        # 2. 连接辅助臂
        print("\n[步骤2] 连接辅助臂（COM4）...")
        puppet_config = SOFollowerRobotConfig(port=PUPPET_PORT)
        puppet = SOFollower(puppet_config)
        puppet.connect(calibrate=False)
        puppet.bus.disable_torque()
        print("✓ 辅助臂连接成功（扭矩已禁用）")
        
        # 3. 准备校准
        print("\n" + "="*70)
        print("校准说明")
        print("="*70)
        print("请按照以下步骤操作：")
        print("  1. 手动移动辅助臂和主臂到不同的位置")
        print("  2. 确保两个臂移动方向一致（辅助臂向上，主臂也向上）")
        print("  3. 每个位置停留2秒，程序会自动记录")
        print("  4. 覆盖所有关节的运动范围：")
        print("     - shoulder_pan（肩部旋转）: 左右转动")
        print("     - shoulder_lift（肩部升降）: 上下移动 ⚠️ 重点检查")
        print("     - elbow_flex（肘部弯曲）: 弯曲/伸直")
        print("     - wrist_flex（腕部弯曲）: 上下摆动")
        print("     - wrist_roll（腕部旋转）: 左右旋转")
        print("     - gripper（夹爪）: 打开/关闭")
        print("  5. 完成后按 Ctrl+C 结束校准")
        print("="*70)
        
        input("\n按 Enter 开始校准...")
        
        # 4. 开始记录
        print("\n[步骤3] 开始记录校准数据...")
        print("提示：移动两个臂到不同的位置，保持方向一致...")
        
        prev_master = None
        prev_puppet = None
        last_record_time = 0
        sample_id = 0
        direction_issues_count = 0
        
        while sample_id < NUM_SAMPLES:
            # 读取当前位置
            master_obs = master.get_observation()
            puppet_obs = puppet.get_observation()
            
            master_dict = get_joint_dict(master_obs)
            puppet_dict = get_joint_dict(puppet_obs)
            
            # 检查是否有移动
            if prev_master is not None:
                # 每2秒记录一次
                current_time = time.time()
                if current_time - last_record_time >= 2.0:
                    # 检查移动量是否足够（至少移动10度）
                    master_moved = any(
                        abs(master_dict.get(j, 0) - prev_master.get(j, 0)) > 10 
                        for j in ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos"]
                    )
                    
                    if master_moved:
                        # 检查方向一致性
                        issues = check_direction_consistency(prev_master, master_dict, 
                                                             prev_puppet, puppet_dict)
                        
                        if issues:
                            print("\n" + "⚠️"*30)
                            print("警告：检测到方向不一致！")
                            for issue in issues:
                                print(f"  {issue['joint']}: 辅助臂移动 {issue['puppet_delta']:.1f}°, "
                                      f"主臂移动 {issue['master_delta']:.1f}°")
                                # 如果有原始数据，也显示（用于调试跨越 ±180° 的情况）
                                if abs(issue.get('master_delta_raw', 0)) > 180:
                                    print(f"    (原始数据: 主臂 {issue['master_delta_raw']:.1f}°，"
                                          f"已归一化处理)")
                            print("\n请调整位置，确保两个臂移动方向一致！")
                            print("例如：如果辅助臂向上，主臂也应该向上")
                            print("⚠️"*30 + "\n")
                            direction_issues_count += 1

                            if direction_issues_count >= 3:
                                print("\n❌ 方向不一致次数过多，请重新检查机械臂安装！")
                                break
                        else:
                            # 记录数据点
                            sample_id += 1
                            data_point = {
                                "sample_id": sample_id,
                                "timestamp": time.time(),
                                "master": master_dict,
                                "puppet": puppet_dict
                            }
                            calibration_data.append(data_point)
                            
                            print(f"✓ 样本 {sample_id}/{NUM_SAMPLES} 已记录")
                            print(f"  主臂 shoulder_lift: {master_dict['shoulder_lift.pos']:.2f}°")
                            print(f"  辅助臂 shoulder_lift: {puppet_dict['shoulder_lift.pos']:.2f}°")
                        
                        last_record_time = current_time
            
            # 更新前一帧数据
            prev_master = master_dict.copy()
            prev_puppet = puppet_dict.copy()
            
            # 打印当前状态（每秒一次）
            if int(time.time() * 2) % 2 == 0:
                print(f"\r[{sample_id}/{NUM_SAMPLES}] "
                      f"主臂: {master_dict['shoulder_lift.pos']:.1f}° | "
                      f"辅助臂: {puppet_dict['shoulder_lift.pos']:.1f}°", end="")
            
            time.sleep(0.1)
        
        # 5. 保存校准数据
        if len(calibration_data) >= 10:
            print(f"\n\n[步骤4] 保存校准数据...")
            
            save_data = {
                "timestamp": datetime.now().isoformat(),
                "num_samples": len(calibration_data),
                "data": calibration_data
            }
            
            # 备份旧数据
            if CALIBRATION_FILE.exists():
                backup_file = Path(f"calibration_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                import shutil
                shutil.copy(CALIBRATION_FILE, backup_file)
                print(f"✓ 旧数据已备份到: {backup_file}")
            
            # 保存新数据
            with open(CALIBRATION_FILE, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            print(f"✓ 校准数据已保存到: {CALIBRATION_FILE}")
            print(f"  共 {len(calibration_data)} 个样本")
            
            # 分析 shoulder_lift 映射
            print("\n[步骤5] 分析 shoulder_lift 映射...")
            shoulder_lift_puppet = [d['puppet']['shoulder_lift.pos'] for d in calibration_data]
            shoulder_lift_master = [d['master']['shoulder_lift.pos'] for d in calibration_data]
            
            puppet_min, puppet_max = min(shoulder_lift_puppet), max(shoulder_lift_puppet)
            master_min, master_max = min(shoulder_lift_master), max(shoulder_lift_master)
            
            print(f"  辅助臂范围: [{puppet_min:.2f}°, {puppet_max:.2f}°]")
            print(f"  主臂范围: [{master_min:.2f}°, {master_max:.2f}°]")
            
            # 检查映射方向
            if (puppet_max > puppet_min) and (master_max > master_min):
                print("  ✓ shoulder_lift 映射方向正确（辅助臂向上 → 主臂向上）")
            else:
                print("  ⚠️ shoulder_lift 映射方向可能仍然有问题，请检查")
        else:
            print(f"\n\n[错误] 样本数量不足（{len(calibration_data)} < 10），校准失败")
    
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断校准")
    
    except Exception as e:
        print(f"\n[错误] 校准失败: {e}")
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
        print("[OK] 校准程序已退出")

if __name__ == "__main__":
    calibrate_with_direction_check()