"""测试控制器连接"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from arm_controller import SoArmController

arm = SoArmController(port='COM3')
arm.connect()
time.sleep(0.3)

status = arm.read_status()
print('电机状态:')
for mid in range(1,7):
    s = status[mid]
    sym = 'OK' if s['status']==0 else 'ERR'
    print(f'  [{sym}] {arm.MOTOR_NAMES[mid]:<15} V={s["voltage"]:.1f}V T={s["temp"]}C status=0x{s["status"]:02X}')

pos = arm.read_all_positions()
print('\n当前位置:')
for mid in range(1,7):
    print(f'  {arm.MOTOR_NAMES[mid]:<15} = {pos[mid]}')

arm.disconnect()
print('\nOK 控制器连接正常')
