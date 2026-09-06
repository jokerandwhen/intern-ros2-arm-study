"""测试关节1（底座旋转）运动范围"""
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
import time

def main():
    print("="*70)
    print("测试关节1（底座旋转）运动范围")
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
        print(f"当前关节1角度: {current_angle:.1f}°")

        # 测试运动范围（物理范围：-139° ~ 89°）
        print("\n[步骤3] 测试运动范围...")

        # 测试负方向（向左）
        test_angles = [-139, -100, -50, 0, 50, 89]

        for target_angle in test_angles:
            print(f"\n尝试移动到 {target_angle}°...")

            try:
                # 发送目标位置
                robot.bus.sync_write("Goal_Position", {"shoulder_pan": float(target_angle)})
                time.sleep(2)

                # 读取实际位置
                actual_pos = robot.bus.sync_read("Present_Position")
                actual_angle = actual_pos.get("shoulder_pan", 0.0)

                # 判断是否到达
                error = abs(actual_angle - target_angle)
                if error < 5:
                    print(f"  ✓ 成功到达 {actual_angle:.1f}° (误差: {error:.1f}°)")
                else:
                    print(f"  ✗ 未到达目标 (目标: {target_angle}°, 实际: {actual_angle:.1f}°, 误差: {error:.1f}°)")

            except Exception as e:
                print(f"  ✗ 移动失败: {e}")

        # 回到中间位置
        print("\n[步骤4] 回到中间位置...")
        robot.bus.sync_write("Goal_Position", {"shoulder_pan": 0.0})
        time.sleep(2)

        # 断开连接
        try:
            robot.disconnect()
        except:
            pass

        print("\n[OK] 测试完成")

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()