"""测试双臂连接"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_controller import SyncController

sync = SyncController(leader_port="COM4", follower_port="COM3")
sync.connect()
time.sleep(0.5)

print("\n--- 主臂 (COM4) ---")
leader_pos = sync.read_all_positions(sync.leader_ser, fast=False)
for mid in range(1, 7):
    print(f"  {sync.MOTOR_NAMES[mid]:<15} = {leader_pos[mid]}")

print("\n--- 从动臂 (COM3) ---")
follower_pos = sync.read_all_positions(sync.follower_ser, fast=False)
for mid in range(1, 7):
    print(f"  {sync.MOTOR_NAMES[mid]:<15} = {follower_pos[mid]}")

sync.disconnect()
print("\nOK 双臂连接正常")
