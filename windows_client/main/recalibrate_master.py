"""
重新校准主臂（COM3）
"""

import os
import shutil
from pathlib import Path

def force_recalibrate_master():
    """强制重新校准主臂"""
    print("="*60)
    print("强制重新校准主臂（COM3）")
    print("="*60)

    # 1. 删除校准文件
    calibration_dir = Path.home() / ".cache" / "huggingface" / "lerobot" / "calibration" / "robots" / "so_follower"

    if calibration_dir.exists():
        print(f"\n[INFO] 删除校准目录: {calibration_dir}")
        shutil.rmtree(calibration_dir)
        print("[OK] 校准文件已删除")

    # 2. 校准主臂
    print("\n[INFO] 开始校准主臂...")
    print("="*60)

    from lerobot.robots.so_follower.so_follower import SOFollower
    from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

    config = SOFollowerRobotConfig(port="COM3")
    robot = SOFollower(config)

    print("\n" + "="*60)
    print("校准说明：")
    print("="*60)
    print("1. 输入 'c' 然后按Enter")
    print("2. 将主臂移动到中间位置，然后按Enter")
    print("3. 缓慢移动每个关节通过完整的运动范围")
    print("4. 完成后按Enter停止记录")
    print("="*60 + "\n")

    robot.connect()

    print("\n[OK] 校准完成！")

    # 3. 测试读取
    print("\n" + "="*60)
    print("测试读取主臂状态")
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
    print("[OK] 主臂重新校准完成！")
    print("="*60)

if __name__ == "__main__":
    force_recalibrate_master()