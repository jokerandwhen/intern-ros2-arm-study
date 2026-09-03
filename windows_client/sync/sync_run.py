"""
SoArm101 主从同步启动脚本

流程:
  1. 连接双臂
  2. 检查电机状态
  3. 校准偏移量（将两臂放在相同位置）
  4. 使能从动臂扭矩
  5. 实时同步：拖动主臂，从动臂跟随
  6. Ctrl+C 停止

用法:
  python sync_run.py              # 默认 COM4主臂, COM3从动臂
  python sync_run.py --invert     # 反转（COM3主臂, COM4从动臂）
"""
import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sync_controller import SyncController

def main():
    parser = argparse.ArgumentParser(description="SoArm101 主从同步")
    parser.add_argument("--invert", action="store_true", help="反转主从（COM3为主臂）")
    parser.add_argument("--leader", default="COM4", help="主臂端口（默认COM4）")
    parser.add_argument("--follower", default="COM3", help="从动臂端口（默认COM3）")
    args = parser.parse_args()
    
    if args.invert:
        args.leader, args.follower = args.follower, args.leader
    
    print("=" * 60)
    print("SoArm101 主从同步")
    print("=" * 60)
    print(f"  主臂（Leader）:   {args.leader}")
    print(f"  从动臂（Follower）: {args.follower}")
    print()
    
    # 连接
    sync = SyncController(leader_port=args.leader, follower_port=args.follower)
    sync.connect()
    time.sleep(0.5)
    
    # 检查状态
    print("\n--- 主臂状态 ---")
    leader_status = sync.read_status(sync.leader_ser)
    for mid in range(1, 7):
        s = leader_status[mid]
        sym = "OK" if s == 0 else "ERR"
        print(f"  [{sym}] {sync.MOTOR_NAMES[mid]:<15} status=0x{s:02X}")
    
    print("\n--- 从动臂状态 ---")
    follower_status = sync.read_status(sync.follower_ser)
    for mid in range(1, 7):
        s = follower_status[mid]
        sym = "OK" if s == 0 else "ERR"
        print(f"  [{sym}] {sync.MOTOR_NAMES[mid]:<15} status=0x{s:02X}")
    
    # 校准
    print("\n" + "=" * 60)
    print("校准阶段")
    print("=" * 60)
    print("请手动将两个机械臂放在相同的位置（姿态一致）")
    print("校准后会计算偏移量，使从动臂跟随主臂运动")
    print("=" * 60)
    
    input("\n摆好位置后按 Enter 校准...")
    
    leader_init, follower_init = sync.calibrate_offsets()
    
    print(f"\n主臂初始位置:   {leader_init}")
    print(f"从动臂初始位置: {follower_init}")
    
    # 使能从动臂扭矩
    print("\n使能从动臂扭矩...")
    sync.enable_follower_torque()
    time.sleep(0.3)
    
    # 先把从动臂稳定在当前位置
    for _ in range(5):
        sync._sync_write_positions(sync.follower_ser, follower_init)
        time.sleep(0.02)
    
    # 同步循环
    print("\n" + "=" * 60)
    print("同步已启动！")
    print("=" * 60)
    print("拖动主臂，从动臂会实时跟随")
    print("按 Ctrl+C 停止\n")
    
    frame = 0
    start_time = time.time()
    
    try:
        while True:
            # 读取主臂位置并同步到从动臂
            leader_pos, target = sync.sync_step()
            
            frame += 1
            
            # 每50帧打印一次状态
            if frame % 50 == 0:
                elapsed = time.time() - start_time
                fps = frame / elapsed
                
                # 读取从动臂实际位置
                follower_actual = sync.read_all_positions(sync.follower_ser, fast=True)
                
                # 计算误差
                errors = {mid: abs(follower_actual[mid] - target[mid]) for mid in range(1, 7)}
                max_err = max(errors.values())
                
                print(f"[f{frame:4d} {elapsed:5.1f}s {fps:4.1f}fps] "
                      f"pan:{leader_pos[1]:4d}->{follower_actual[1]:4d} "
                      f"lift:{leader_pos[2]:4d}->{follower_actual[2]:4d} "
                      f"elbow:{leader_pos[3]:4d}->{follower_actual[3]:4d} "
                      f"grip:{leader_pos[6]:4d}->{follower_actual[6]:4d} "
                      f"err:{max_err:3d}")
            
            time.sleep(0.02)  # ~50Hz
    
    except KeyboardInterrupt:
        print("\n\n停止同步...")
    
    finally:
        sync.disable_all_torque()
        sync.disconnect()
        elapsed = time.time() - start_time
        print(f"\n运行时长: {elapsed:.1f}s, 总帧数: {frame}, 平均帧率: {frame/elapsed:.1f}fps")
        print("完成")

if __name__ == "__main__":
    main()
