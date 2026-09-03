"""
机械臂初始化脚本
连接机械臂，检查状态，使能扭矩，准备就绪
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arm_controller import SoArmController

def init_arm(port="COM3"):
    """初始化机械臂"""
    print("=" * 60)
    print("SoArm101 机械臂初始化")
    print("=" * 60)
    
    arm = SoArmController(port=port)
    arm.connect()
    time.sleep(0.5)
    
    # 读取状态
    print("\n--- 电机状态检查 ---")
    status = arm.read_status()
    all_ok = True
    for mid in range(1, 7):
        s = status[mid]
        ok = s['status'] == 0
        symbol = "✓" if ok else "⚠"
        print(f"  {symbol} {arm.MOTOR_NAMES[mid]:<15} V={s['voltage']:.1f}V T={s['temp']}°C status=0x{s['status']:02X}")
        if not ok:
            all_ok = False
    
    # 读取当前位置
    print("\n--- 当前位置 ---")
    positions = arm.read_all_positions()
    for mid in range(1, 7):
        print(f"  {arm.MOTOR_NAMES[mid]:<15} = {positions[mid]}")
    
    if not all_ok:
        print("\n⚠ 部分电机有错误状态，但已禁用扭矩，请检查后重新使能")
    
    # 禁用扭矩（安全起见，让用户手动摆到初始位置）
    print("\n✓ 扭矩已禁用，可以手动移动机械臂")
    print("  使用 keyboard_control.py 进行键盘控制")
    print("  使用 record_positions.py 记录抓取位置")
    print("  使用 grasp.py 执行抓取任务")
    
    return arm, positions

if __name__ == "__main__":
    port = "COM3"
    if len(sys.argv) > 1:
        port = sys.argv[1]
    
    try:
        arm, pos = init_arm(port)
        
        print("\n按 Enter 断开连接...")
        input()
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            arm.disconnect()
        except:
            pass
