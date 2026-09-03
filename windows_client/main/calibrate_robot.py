"""
SoArm101机械臂校准脚本
红色LED灯通常表示机械臂需要首次校准

校准步骤：
1. 机械臂上电（电源适配器）
2. USB连接到电脑（COM3或其他端口）
3. 运行校准命令
4. 按照提示手动移动机械臂到各个校准位置
"""

import subprocess
import sys

# 配置
ROBOT_PORT = "COM3"  # 根据实际情况修改
ROBOT_ID = "my_soarm101"  # 机械臂ID（自定义名称）

print("=" * 60)
print("SoArm101 机械臂校准工具")
print("=" * 60)
print(f"串口: {ROBOT_PORT}")
print(f"ID: {ROBOT_ID}")
print("=" * 60)
print()
print("注意事项：")
print("1. 确保机械臂已上电（电源适配器已连接）")
print("2. 确保USB线已连接到电脑")
print("3. 校准过程中需要手动移动机械臂")
print("4. 请勿在校准过程中强制移动机械臂")
print()
print("即将开始校准...")
print()

# 运行lerobot校准命令
# 注意：so101_follower是SoArm101的正确类型
cmd = [
    "lerobot-calibrate",
    f"--robot.type=so101_follower",
    f"--robot.port={ROBOT_PORT}",
    f"--robot.id={ROBOT_ID}"
]

print("执行命令:", " ".join(cmd))
print()

# 执行校准
try:
    result = subprocess.run(cmd, check=True)
    print("\n" + "=" * 60)
    print("校准完成！")
    print("=" * 60)
except subprocess.CalledProcessError as e:
    print("\n" + "=" * 60)
    print(f"校准失败: {e}")
    print("=" * 60)
    print()
    print("可能的原因：")
    print("1. 机械臂未上电")
    print("2. 串口号错误（请检查设备管理器）")
    print("3. 机械臂硬件问题")
    sys.exit(1)
except KeyboardInterrupt:
    print("\n用户取消校准")
    sys.exit(0)