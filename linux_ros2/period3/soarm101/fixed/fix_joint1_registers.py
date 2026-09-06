"""读取和修改关节1（shoulder_pan）舵机内部位置限制寄存器"""
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
import time

# SCS/STS 舵机常见寄存器地址（需要根据具体型号确认）
# Feetech/STS SCS 系列寄存器参考：
# Min_Position_Limit = 20 (0x14)
# Max_Position_Limit = 22 (0x16)
# Acceleration = 41 (0x29)

def read_register(robot, joint_name, addr, length=2):
    """读取指定地址的寄存器"""
    try:
        # 使用 _read 方法读取原始寄存器
        if length == 2:
            return robot.bus._read(addr, joint_name)
        else:
            return robot.bus._read(addr, joint_name, num_bytes=length)
    except Exception as e:
        print(f"  读取 0x{addr:02X} 失败: {e}")
        return None

def write_register(robot, joint_name, addr, value, length=2):
    """写入指定地址的寄存器"""
    try:
        robot.bus._write(addr, joint_name, value, num_bytes=length)
        return True
    except Exception as e:
        print(f"  写入 0x{addr:02X} 失败: {e}")
        return False

def main():
    print("="*70)
    print("修复关节1舵机内部位置限制寄存器")
    print("="*70)

    try:
        # 连接机械臂
        print("\n[步骤1] 连接机械臂...")
        config = SOFollowerRobotConfig(port="/dev/ttyACM0")
        robot = SOFollower(config)
        robot.connect()
        print("[OK] 连接成功")

        # 读取当前位置
        print("\n[步骤2] 读取当前位置...")
        current_pos = robot.bus.sync_read("Present_Position")
        current_angle = current_pos.get("shoulder_pan", 0.0)
        print(f"当前 shoulder_pan 角度: {current_angle:.1f}°")

        # 尝试读取内部限制寄存器
        print("\n[步骤3] 读取内部位置限制寄存器...")

        # 使用 lerobot 已知寄存器名称读取
        registers_to_check = [
            ("Min_Position_Limit", "最小位置限制"),
            ("Max_Position_Limit", "最大位置限制"),
            ("Acceleration", "加速度限制"),
            ("Max_Torque_Limit", "最大扭矩限制"),
            ("Goal_Position", "目标位置"),
            ("Present_Position", "当前位置"),
        ]

        for reg_name, desc in registers_to_check:
            try:
                value = robot.bus.read(reg_name, "shoulder_pan")
                print(f"  {desc} ({reg_name}): {value}")
            except Exception as e:
                print(f"  {desc} ({reg_name}): 读取失败 - {e}")

        # 写入最大位置范围
        print("\n[步骤4] 修改位置限制寄存器...")
        print("  将 Min_Position_Limit 设为 0")
        print("  将 Max_Position_Limit 设为 4095")

        # 先禁用扭矩，再修改参数
        try:
            robot.bus.write("Torque_Enable", "shoulder_pan", 0)
            time.sleep(0.5)
        except Exception as e:
            print(f"  禁用扭矩失败: {e}")

        # 尝试写入限制寄存器
        try:
            robot.bus.write("Min_Position_Limit", "shoulder_pan", 0)
            print("  ✓ Min_Position_Limit 已设为 0")
        except Exception as e:
            print(f"  ✗ Min_Position_Limit 写入失败: {e}")

        try:
            robot.bus.write("Max_Position_Limit", "shoulder_pan", 4095)
            print("  ✓ Max_Position_Limit 已设为 4095")
        except Exception as e:
            print(f"  ✗ Max_Position_Limit 写入失败: {e}")

        try:
            robot.bus.write("Acceleration", "shoulder_pan", 25)
            print("  ✓ Acceleration 已设为 25")
        except Exception as e:
            print(f"  ✗ Acceleration 写入失败: {e}")

        # 重新启用扭矩
        try:
            robot.bus.write("Torque_Enable", "shoulder_pan", 1)
            time.sleep(0.5)
            print("  ✓ 扭矩已重新启用")
        except Exception as e:
            print(f"  ✗ 启用扭矩失败: {e}")

        # 验证修改后的寄存器
        print("\n[步骤5] 验证修改后的寄存器...")
        try:
            min_limit = robot.bus.read("Min_Position_Limit", "shoulder_pan")
            print(f"  Min_Position_Limit: {min_limit}")
        except Exception as e:
            print(f"  Min_Position_Limit 读取失败: {e}")

        try:
            max_limit = robot.bus.read("Max_Position_Limit", "shoulder_pan")
            print(f"  Max_Position_Limit: {max_limit}")
        except Exception as e:
            print(f"  Max_Position_Limit 读取失败: {e}")

        # 测试大范围移动
        print("\n[步骤6] 测试大范围移动...")
        test_angles = [-139, -50, 0, 50, 89]
        for target_angle in test_angles:
            try:
                print(f"\n  尝试移动到 {target_angle}°...", end=" ")
                robot.bus.sync_write("Goal_Position", {"shoulder_pan": float(target_angle)})
                time.sleep(3)

                actual_pos = robot.bus.sync_read("Present_Position")
                actual_angle = actual_pos.get("shoulder_pan", 0.0)
                error = abs(actual_angle - target_angle)

                if error < 5:
                    print(f"✓ 成功到达 {actual_angle:.1f}°")
                else:
                    print(f"✗ 实际: {actual_angle:.1f}° (误差 {error:.1f}°)")
            except Exception as e:
                print(f"✗ 失败: {e}")

        # 断开连接
        try:
            robot.disconnect()
        except:
            pass

        print("\n[OK] 修复完成")

    except Exception as e:
        print(f"\n[ERROR] 程序失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
