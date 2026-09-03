"""
检查主臂夹爪电机位置读取
"""

import time
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def check_master_gripper():
    """检查主臂夹爪是否能正确读取位置"""
    
    print("="*70)
    print("主臂夹爪电机位置读取检查")
    print("="*70)
    print("\n这个脚本会实时显示主臂夹爪的位置变化")
    print("请手动移动主臂夹爪，观察数值是否变化")
    print("="*70)
    
    master = None
    
    try:
        # 连接主臂
        print("\n[步骤1] 连接主臂（COM3）...")
        master_config = SOFollowerRobotConfig(port="COM3")
        master = SOFollower(master_config)
        master.connect(calibrate=False)
        master.bus.disable_torque()
        print("✓ 主臂连接成功")
        
        # 实时监控夹爪位置（使用原始寄存器值）
        print("\n[步骤2] 实时监控夹爪位置...")
        print("使用原始寄存器值（0-4095）读取")
        print("请手动开合主臂夹爪...")
        print("按 Ctrl+C 停止\n")
        
        positions = []
        frame = 0
        
        while True:
            try:
                # 直接读取寄存器（使用原始值，normalize=False）
                gripper_pos = master.bus.read("Present_Position", "gripper", normalize=False)
                
                # 记录位置
                positions.append(gripper_pos)
                
                # 显示
                frame += 1
                print(f"[帧{frame}] 主臂夹爪位置（原始值）: {gripper_pos} (0-4095)")
                
                # 每秒统计一次范围
                if frame % 20 == 0 and len(positions) > 0:
                    min_pos = min(positions[-20:])
                    max_pos = max(positions[-20:])
                    range_pos = max_pos - min_pos
                    
                    print(f"  → 最近20帧范围: [{min_pos}, {max_pos}], 变化量: {range_pos}")
                    
                    if range_pos < 10:
                        print("  ⚠️ 夹爪位置几乎没有变化！")
                    else:
                        print("  ✓ 夹爪位置有正常变化")
            
            except Exception as e:
                print(f"  [错误] 读取失败: {e}")
                time.sleep(0.1)
            
            time.sleep(0.05)
    
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断")
        
        # 统计
        if len(positions) > 0:
            print("\n夹爪位置统计:")
            print(f"  最小值: {min(positions):.2f}")
            print(f"  最大值: {max(positions):.2f}")
            print(f"  变化范围: {max(positions) - min(positions):.2f}")
            
            if max(positions) - min(positions) < 5.0:
                print("\n⚠️ 主臂夹爪位置读取异常（变化范围 < 5°）")
                print("可能原因：")
                print("  1. 夹爪电机连接松动")
                print("  2. 夹爪电机位置传感器故障")
                print("  3. 夹爪电机需要重新校准")
            else:
                print("\n✓ 主臂夹爪位置读取正常")
    
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if master:
            try:
                master.disconnect()
            except:
                pass

if __name__ == "__main__":
    check_master_gripper()