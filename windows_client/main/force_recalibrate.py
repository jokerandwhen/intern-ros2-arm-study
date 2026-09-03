"""
强制重新校准辅助臂（COM4）
删除旧校准文件并重新校准
"""

import os
import shutil
from pathlib import Path

def force_recalibrate_puppet():
    """强制重新校准辅助臂"""
    print("="*60)
    print("强制重新校准辅助臂（COM4）")
    print("="*60)
    
    # 1. 删除所有校准文件
    calibration_dir = Path.home() / ".cache" / "huggingface" / "lerobot" / "calibration" / "robots" / "so_follower"
    
    if calibration_dir.exists():
        print(f"\n[INFO] 删除校准目录: {calibration_dir}")
        shutil.rmtree(calibration_dir)
        print("[OK] 校准文件已删除")
    else:
        print("[INFO] 校准目录不存在，无需删除")
    
    # 2. 导入并运行校准
    print("\n[INFO] 开始校准辅助臂...")
    print("="*60)
    
    from lerobot.robots.so_follower.so_follower import SOFollower
    from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
    
    # 连接并强制校准
    config = SOFollowerRobotConfig(port="COM4")
    robot = SOFollower(config)
    
    print("\n" + "="*60)
    print("校准说明：")
    print("="*60)
    print("1. 当提示时，输入 'c' 然后按Enter")
    print("2. 将辅助臂移动到中间位置，然后按Enter")
    print("3. 缓慢移动每个关节通过完整的运动范围：")
    print("   - shoulder_pan（肩部旋转）")
    print("   - shoulder_lift（肩部升降）")
    print("   - elbow_flex（肘部弯曲）")
    print("   - wrist_flex（腕部弯曲）")
    print("   - gripper（夹爪）")
    print("4. 完成后按Enter停止记录")
    print("="*60 + "\n")
    
    robot.connect()
    
    print("\n[OK] 校准完成！")
    
    # 3. 测试读取
    print("\n" + "="*60)
    print("测试读取辅助臂状态")
    print("="*60)
    
    obs = robot.get_observation()
    print(f"[DEBUG] 观测数据: {obs}")
    
    if isinstance(obs, dict):
        print("\n关节角度（应该在-100到100之间）：")
        for key, value in obs.items():
            status = "✓ 正常" if -100 <= value <= 100 else "✗ 异常"
            print(f"  {key}: {value:.2f} {status}")
    
    robot.disconnect()
    
    print("\n" + "="*60)
    print("[OK] 辅助臂重新校准完成！")
    print("="*60)

if __name__ == "__main__":
    force_recalibrate_puppet()