#!/usr/bin/env python3
"""
修复舵机角度限制
将所有舵机的 min/max 角度限制恢复正常值 (0-4095)
"""
import time
import scservo_sdk as scs

# 舵机ID列表
SERVO_IDS = [1, 2, 3, 4, 5, 6]

# 控制表地址
ADDR_MIN_ANGLE_LIMIT = 30
ADDR_MAX_ANGLE_LIMIT = 32
ADDR_TORQUE_ENABLE = 40

def main():
    print("=" * 60)
    print("舵机角度限制修复工具")
    print("=" * 60)

    port = scs.PortHandler('/dev/ttyACM0')
    ph = scs.PacketHandler(0)

    if not port.openPort():
        print("[错误] 无法打开端口 /dev/ttyACM0")
        return

    if not port.setBaudRate(1000000):
        print("[错误] 无法设置波特率 1000000")
        port.closePort()
        return

    print("\n✓ 已连接到舵机总线")

    for servo_id in SERVO_IDS:
        print(f"\n[舵机 {servo_id}]")

        # 1. 读取当前角度限制
        min_val, r1, _ = ph.read2ByteTxRx(port, servo_id, ADDR_MIN_ANGLE_LIMIT)
        max_val, r2, _ = ph.read2ByteTxRx(port, servo_id, ADDR_MAX_ANGLE_LIMIT)

        if r1 == 0 and r2 == 0:
            print(f"  当前角度限制: {min_val}~{max_val} ({min_val*360/4096:.1f}°~{max_val*360/4096:.1f}°)")
        else:
            print(f"  [警告] 无法读取当前值")

        # 2. 禁用扭矩（必须先禁用才能写入角度限制）
        result, _ = ph.write1ByteTxRx(port, servo_id, ADDR_TORQUE_ENABLE, 0)
        if result != 0:
            print(f"  [警告] 禁用扭矩失败")
        time.sleep(0.1)

        # 3. 写入正常角度限制
        print(f"  正在修复角度限制为 0~4095 (0°~360°)...")
        result1, _ = ph.write2ByteTxRx(port, servo_id, ADDR_MIN_ANGLE_LIMIT, 0)
        result2, _ = ph.write2ByteTxRx(port, servo_id, ADDR_MAX_ANGLE_LIMIT, 4095)

        if result1 == 0 and result2 == 0:
            print(f"  ✓ 角度限制已修复")
        else:
            print(f"  [错误] 写入失败")

        time.sleep(0.1)

        # 4. 验证
        min_val, r1, _ = ph.read2ByteTxRx(port, servo_id, ADDR_MIN_ANGLE_LIMIT)
        max_val, r2, _ = ph.read2ByteTxRx(port, servo_id, ADDR_MAX_ANGLE_LIMIT)

        if r1 == 0 and r2 == 0:
            print(f"  验证: {min_val}~{max_val} ({min_val*360/4096:.1f}°~{max_val*360/4096:.1f}°)")
        else:
            print(f"  [警告] 无法验证")

        # 5. 重新启用扭矩
        result, _ = ph.write1ByteTxRx(port, servo_id, ADDR_TORQUE_ENABLE, 1)
        if result == 0:
            print(f"  ✓ 扭矩已启用")
        time.sleep(0.1)

    port.closePort()
    print("\n" + "=" * 60)
    print("修复完成！所有舵机角度限制已恢复为 0°~360°")
    print("=" * 60)

if __name__ == '__main__':
    main()