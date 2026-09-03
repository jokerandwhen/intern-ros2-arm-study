"""
直接读取夹爪电机的原始值
尝试绕过norm_mode，读取原始寄存器
"""

import time
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
from lerobot.motors.feetech import FeetechMotorsBus

def read_raw_gripper():
    """读取夹爪电机的原始值"""

    print("="*70)
    print("读取夹爪电机的原始值")
    print("="*70)

    master = None
    try:
        # 连接主臂
        print("\n[步骤1] 连接主臂（COM3）...")
        master_config = SOFollowerRobotConfig(port="COM3")
        master = SOFollower(master_config)
        master.connect(calibrate=False)

        print("✓ 主臂连接成功")

        # 尝试使用 sync_read 读取所有电机
        print("\n[步骤2] 使用 sync_read 读取所有电机...")
        try:
            positions = master.bus.sync_read("Present_Position")
            print("  所有电机位置:")
            for motor_name, pos in positions.items():
                print(f"    {motor_name}: {pos:.2f}")
        except Exception as e:
            print(f"  sync_read 失败: {e}")

        # 尝试读取夹爪的其他寄存器
        print("\n[步骤3] 读取夹爪电机的其他寄存器...")
        try:
            # 尝试读取 Present_Load
            loads = master.bus.sync_read("Present_Load")
            if 'gripper' in loads:
                print(f"  夹爪负载: {loads['gripper']:.2f}")

            # 尝试读取 Present_Voltage
            voltages = master.bus.sync_read("Present_Voltage")
            if 'gripper' in voltages:
                print(f"  夹爪电压: {voltages['gripper']:.2f}")

            # 尝试读取 Present_Temperature
            temps = master.bus.sync_read("Present_Temperature")
            if 'gripper' in temps:
                print(f"  夹爪温度: {temps['gripper']:.2f}")

        except Exception as e:
            print(f"  读取其他寄存器失败: {e}")

        # 实时监控夹爪位置
        print("\n[步骤4] 实时监控夹爪位置...")
        print("请手动移动主臂夹爪...")
        print("按 Ctrl+C 停止\n")

        frame = 0
        last_pos = None
        while True:
            try:
                positions = master.bus.sync_read("Present_Position")
                gripper_pos = positions.get('gripper', 0)

                # 每秒打印一次
                if frame % 10 == 0:
                    print(f"[帧{frame}] 夹爪位置: {gripper_pos:.2f}")

                # 检测变化
                if last_pos is not None and abs(gripper_pos - last_pos) > 1.0:
                    print(f"  ⚠️ 检测到夹爪移动！新位置: {gripper_pos:.2f}")
                    last_pos = gripper_pos

                if last_pos is None:
                    last_pos = gripper_pos

            except Exception as e:
                print(f"[帧{frame}] 读取失败: {e}")

            frame += 1
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n[INFO] 监控已停止")

    except Exception as e:
        print(f"\n[错误] 诊断失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n[断开连接]")
        if master:
            try:
                master.disconnect()
            except:
                pass
        print("[OK] 诊断完成")

if __name__ == "__main__":
    read_raw_gripper()