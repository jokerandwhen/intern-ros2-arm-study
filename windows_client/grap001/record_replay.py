"""
SoArm101 动作录制与回放

模式:
  1. 录制模式 - 禁用扭矩，你手动移动机械臂，程序按固定频率记录所有关节位置
  2. 回放模式 - 使能扭矩，按录制的轨迹逐帧复刻动作

用法:
  python record_replay.py record [任务名]   # 录制动作
  python record_replay.py replay [任务名]   # 回放动作
  python record_replay.py list              # 查看已录制的任务
  python record_replay.py delete [任务名]   # 删除某个任务
"""
import sys
import os
import time
import json
import msvcrt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arm_controller import SoArmController

RECORDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "records")
RECORD_FREQ = 20  # 录制频率 Hz（每秒记录20帧）
REPLAY_SPEED = 1.0  # 回放速度倍率

def ensure_records_dir():
    if not os.path.exists(RECORDS_DIR):
        os.makedirs(RECORDS_DIR)

def get_record_path(name):
    return os.path.join(RECORDS_DIR, f"{name}.json")

def list_records():
    ensure_records_dir()
    files = [f[:-5] for f in os.listdir(RECORDS_DIR) if f.endswith('.json')]
    return sorted(files)

def record(arm, name):
    """录制模式：禁用扭矩，实时记录手动移动"""
    print("\n" + "=" * 60)
    print(f"录制模式: {name}")
    print("=" * 60)
    
    # 禁用扭矩，让用户手动移动
    print("禁用扭矩，你可以手动移动机械臂...")
    arm.disable_torque()
    time.sleep(0.5)
    
    # 读取当前位置
    start_pos = arm.read_all_positions_fast()
    print(f"\n起始位置: {start_pos}")
    
    print(f"\n录制频率: {RECORD_FREQ} Hz (每秒{RECORD_FREQ}帧)")
    print("\n操作说明:")
    print("  1. 手动将机械臂摆到起始位置")
    print("  2. 按 Enter 开始录制")
    print("  3. 手动移动机械臂完成动作")
    print("  4. 按 Esc 或 Ctrl+C 停止录制")
    print()
    
    input("准备好后按 Enter 开始录制...")
    
    frames = []
    start_time = time.time()
    frame_interval = 1.0 / RECORD_FREQ
    
    print("录制中... (按 Esc 停止)")
    print(f"{'时间':>6}s  {'帧数':>5}  shoulder  lift   elbow  wrist_f wrist_r gripper")
    print("-" * 75)
    
    try:
        next_frame_time = start_time
        while True:
            # 检查Esc键
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\x1b':  # Esc
                    break
            
            current_time = time.time()
            elapsed = current_time - start_time
            
            # 读取位置（高速）
            pos = arm.read_all_positions_fast()
            frames.append({
                't': round(elapsed, 4),
                'pos': {str(k): v for k, v in pos.items()}
            })
            
            # 打印进度
            if len(frames) % 10 == 1:
                print(f"{elapsed:6.2f}s  {len(frames):5d}  "
                      f"{pos[1]:7d}  {pos[2]:5d}  {pos[3]:5d}  "
                      f"{pos[4]:6d}  {pos[5]:6d}  {pos[6]:6d}")
            
            # 等待下一帧
            next_frame_time += frame_interval
            sleep_time = next_frame_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    except KeyboardInterrupt:
        pass
    
    duration = time.time() - start_time
    print("-" * 75)
    print(f"\n录制完成!")
    print(f"  总时长: {duration:.2f}s")
    print(f"  总帧数: {len(frames)}")
    print(f"  实际频率: {len(frames)/duration:.1f} Hz")
    
    if len(frames) < 2:
        print("\n录制太短，未保存")
        return
    
    # 保存
    ensure_records_dir()
    record_data = {
        'name': name,
        'freq': RECORD_FREQ,
        'duration': round(duration, 2),
        'frames': len(frames),
        'data': frames
    }
    
    path = get_record_path(name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(record_data, f, indent=2)
    print(f"  已保存到: {path}")

def replay(arm, name):
    """回放模式：使能扭矩，按录制的轨迹复刻"""
    path = get_record_path(name)
    if not os.path.exists(path):
        print(f"\n录制 '{name}' 不存在")
        print(f"可用录制: {', '.join(list_records())}")
        return
    
    with open(path, 'r', encoding='utf-8') as f:
        record_data = json.load(f)
    
    frames = record_data['data']
    duration = record_data['duration']
    
    print("\n" + "=" * 60)
    print(f"回放模式: {name}")
    print("=" * 60)
    print(f"  录制时长: {duration}s")
    print(f"  帧数: {len(frames)}")
    print(f"  回放速度: {REPLAY_SPEED}x")
    
    # 显示第一帧（起始位置）
    first_frame = frames[0]
    start_pos = {int(k): v for k, v in first_frame['pos'].items()}
    print(f"\n  起始位置: {start_pos}")
    
    print("\n操作说明:")
    print("  1. 确认机械臂当前位置与录制起始位置接近")
    print("  2. 按 Enter 开始回放")
    print("  3. 按 Ctrl+C 可随时停止")
    
    input("\n准备好后按 Enter 开始回放...")
    
    # 使能扭矩
    print("使能扭矩...")
    arm.enable_torque()
    time.sleep(0.5)
    
    # 先平滑移动到起始位置
    print("移动到起始位置...")
    arm.move_smooth(start_pos, steps=20, delay=0.03)
    time.sleep(0.3)
    
    print("\n回放中...")
    print(f"{'时间':>6}s  {'帧':>5}/{len(frames)}  shoulder  lift   elbow  wrist_f wrist_r gripper")
    print("-" * 75)
    
    start_time = time.time()
    frame_interval = (1.0 / RECORD_FREQ) / REPLAY_SPEED
    
    try:
        for i, frame in enumerate(frames):
            # 检查Ctrl+C
            target = {int(k): v for k, v in frame['pos'].items()}
            arm._sync_write_positions(target)
            
            elapsed = time.time() - start_time
            
            if (i + 1) % 10 == 0 or i == 0 or i == len(frames) - 1:
                print(f"{elapsed:6.2f}s  {i+1:5d}/{len(frames)}  "
                      f"{target[1]:7d}  {target[2]:5d}  {target[3]:5d}  "
                      f"{target[4]:6d}  {target[5]:6d}  {target[6]:6d}")
            
            # 等待下一帧时间
            expected_time = (i + 1) * frame_interval
            actual_time = time.time() - start_time
            sleep_time = expected_time - actual_time
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        actual_duration = time.time() - start_time
        print("-" * 75)
        print(f"\n回放完成! 实际时长: {actual_duration:.2f}s")
        
    except KeyboardInterrupt:
        print("\n\n回放被中断")
    
    finally:
        arm.disable_torque()

def smooth_replay(arm, name):
    """平滑回放模式：在帧之间插值，运动更平滑"""
    path = get_record_path(name)
    if not os.path.exists(path):
        print(f"\n录制 '{name}' 不存在")
        return
    
    with open(path, 'r', encoding='utf-8') as f:
        record_data = json.load(f)
    
    frames = record_data['data']
    
    print("\n" + "=" * 60)
    print(f"平滑回放: {name}")
    print("=" * 60)
    print(f"  帧数: {len(frames)}, 时长: {record_data['duration']}s")
    
    input("\n按 Enter 开始平滑回放...")
    
    arm.enable_torque()
    time.sleep(0.3)
    
    # 移动到起始位置
    first_pos = {int(k): v for k, v in frames[0]['pos'].items()}
    arm.move_smooth(first_pos, steps=20, delay=0.03)
    time.sleep(0.3)
    
    print("回放中...")
    
    frame_interval = 1.0 / RECORD_FREQ
    interp_steps = 3  # 每帧之间插值3步
    
    start_time = time.time()
    
    try:
        for i in range(len(frames) - 1):
            curr = {int(k): v for k, v in frames[i]['pos'].items()}
            next_f = {int(k): v for k, v in frames[i+1]['pos'].items()}
            
            for s in range(1, interp_steps + 1):
                t = s / interp_steps
                target = {}
                for mid in range(1, 7):
                    target[mid] = int(curr[mid] + (next_f[mid] - curr[mid]) * t)
                arm._sync_write_positions(target)
                time.sleep(frame_interval / interp_steps)
            
            elapsed = time.time() - start_time
            if (i + 1) % 20 == 0:
                print(f"  {elapsed:.1f}s  {i+1}/{len(frames)}帧")
        
        # 最后一帧
        last_pos = {int(k): v for k, v in frames[-1]['pos'].items()}
        arm._sync_write_positions(last_pos)
        
        print(f"\n回放完成! {time.time()-start_time:.2f}s")
    
    except KeyboardInterrupt:
        print("\n\n回放被中断")
    finally:
        arm.disable_torque()

def main():
    print("=" * 60)
    print("SoArm101 动作录制与回放")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n已录制动作:")
        records = list_records()
        if records:
            for r in records:
                path = get_record_path(r)
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"  {r:<20} {data['duration']}s  {data['frames']}帧")
        else:
            print("  (暂无)")
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == 'list':
        records = list_records()
        if records:
            print("\n已录制动作:")
            for r in records:
                path = get_record_path(r)
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"  {r:<20} {data['duration']}s  {data['frames']}帧")
        else:
            print("\n暂无录制")
        return
    
    if cmd == 'delete':
        if len(sys.argv) < 3:
            print("用法: python record_replay.py delete <任务名>")
            return
        name = sys.argv[2]
        path = get_record_path(name)
        if os.path.exists(path):
            os.remove(path)
            print(f"已删除 '{name}'")
        else:
            print(f"'{name}' 不存在")
        return
    
    if cmd not in ('record', 'replay', 'smooth'):
        print(__doc__)
        return
    
    name = sys.argv[2] if len(sys.argv) > 2 else "task1"
    
    arm = SoArmController(port="COM3")
    arm.connect()
    time.sleep(0.3)
    
    # 检查状态
    status = arm.read_status()
    for mid in range(1, 7):
        if status[mid]['status'] != 0:
            print(f"  电机{mid}状态: 0x{status[mid]['status']:02X}")
    
    try:
        if cmd == 'record':
            record(arm, name)
        elif cmd == 'replay':
            replay(arm, name)
        elif cmd == 'smooth':
            smooth_replay(arm, name)
    finally:
        arm.disconnect()

if __name__ == "__main__":
    main()
