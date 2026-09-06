"""SO-ARM100 机械臂控制程序 - 支持姿态记录与分析"""
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
import json
import os
import time
import select
import sys
import tty
import termios

# 文件路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JOINT_RANGE_FILE = os.path.join(SCRIPT_DIR, "joint_range.json")
POSES_FILE = os.path.join(SCRIPT_DIR, "poses.json")

# 关节配置
JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
JOINT_MIN = [-139.0, -90.0, -135.0, -90.0, -180.0, 0.0]  # shoulder_pan 实际范围 -139° ~ 89°
JOINT_MAX = [89.0, 90.0, 0.0, 90.0, 180.0, 100.0]  # elbow_flex 只能用负数角度

class KeyboardInput:
    """Linux键盘非阻塞输入"""
    def __init__(self):
        self.old_settings = termios.tcgetattr(sys.stdin)
    
    def __enter__(self):
        tty.setcbreak(sys.stdin.fileno())
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
    
    def kbhit(self):
        return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])
    
    def getch(self):
        return sys.stdin.read(1)

def load_poses():
    """加载已保存的姿态"""
    if os.path.exists(POSES_FILE):
        with open(POSES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get("poses", [])
    return []

def save_poses(poses):
    """保存姿态到文件"""
    with open(POSES_FILE, 'w', encoding='utf-8') as f:
        json.dump({"poses": poses}, f, indent=4, ensure_ascii=False)

def print_status(angles, selected_joint, angle_step):
    """打印当前状态"""
    print("\n" + "="*70)
    print("SO-ARM100 机械臂控制 - 按 H 查看帮助")
    print("="*70)
    print(f"步长: {angle_step}° | 选中关节: {selected_joint + 1}. {JOINT_NAMES[selected_joint]}")
    print("-"*70)
    for i, name in enumerate(JOINT_NAMES):
        marker = ">>> " if i == selected_joint else "    "
        angle = angles[i]
        min_val, max_val = JOINT_MIN[i], JOINT_MAX[i]
        bar_len = 20
        progress = (angle - min_val) / (max_val - min_val) * bar_len
        bar = "[" + "="*int(progress) + " "*(bar_len - int(progress)) + "]"
        status = ""
        if angle <= min_val + 1:
            status = " [MIN]"
        elif angle >= max_val - 1:
            status = " [MAX]"
        print(f"{marker}{i+1}. {name:15s}: {angle:7.1f}° {bar} [{min_val:7.1f}° ~ {max_val:7.1f}°]{status}")
    print("-"*70)
    print(f"已记录姿态数: {len(load_poses())}")
    print("="*70)

def print_help():
    """打印帮助信息"""
    print("\n" + "="*70)
    print("帮助信息")
    print("="*70)
    print("  1-6      : 选择关节 (底座/肩/肘/腕1/腕2/夹爪)")
    print("  W/↑      : 增加角度")
    print("  S/↓      : 减小角度")
    print("  T/E/R    : 设置步长 (1°/5°/10°)")
    print("  H        : 显示此帮助")
    print("  Space    : 记录当前姿态")
    print("  L        : 列出所有姿态")
    print("  A        : 分析姿态差异")
    print("  P        : 播放/加载姿态")
    print("  C        : 清除舵机过载错误")
    print("  Z        : 归位 (所有关节回安全位置)")
    print("  ESC/Q    : 退出程序")
    print("="*70)

def print_poses(poses):
    """打印所有已记录的姿态"""
    if not poses:
        print("\n[INFO] 暂无记录的姿态")
        return
    
    print("\n" + "="*70)
    print(f"已记录的姿态 (共 {len(poses)} 个)")
    print("="*70)
    for i, pose in enumerate(poses):
        print(f"\n姿态 {i+1}: {pose['name']}")
        print(f"  时间: {pose['timestamp']}")
        print("  关节角度:")
        for name, angle in pose['angles'].items():
            print(f"    {name}: {angle:.1f}°")
    print("="*70)

def analyze_poses(poses):
    """分析姿态差异"""
    if len(poses) < 2:
        print("\n[INFO] 至少需要2个姿态才能分析差异")
        return
    
    print("\n" + "="*70)
    print("姿态差异分析")
    print("="*70)
    
    for i in range(len(poses) - 1):
        p1, p2 = poses[i], poses[i+1]
        print(f"\n姿态 {i+1} ({p1['name']}) -> 姿态 {i+2} ({p2['name']}):")
        print("-"*50)
        for name in JOINT_NAMES:
            a1 = p1['angles'][name]
            a2 = p2['angles'][name]
            diff = a2 - a1
            print(f"  {name:15s}: {a1:7.1f}° -> {a2:7.1f}° (变化: {diff:+7.1f}°)")
    
    print("="*70)

def clear_overload_error(robot, joint_names):
    """清除舵机过载错误"""
    print("\n[INFO] 清除舵机过载错误...")
    try:
        # 重新使能所有舵机
        for name in joint_names:
            try:
                robot.bus.write("Torque_Enable", name, 1)
                print(f"  {name}: 已重新使能")
            except Exception as e:
                print(f"  {name}: {e}")
        print("[OK] 清除完成")
    except Exception as e:
        print(f"[ERROR] 清除失败: {e}")

def main():
    print("="*70)
    print("SO-ARM100 机械臂控制程序")
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
        print("当前位置:", {k: round(v, 1) for k, v in current_pos.items()})
        
        # 初始化角度数组（使用当前位置，避免触发过载）
        angles = [
            current_pos.get("shoulder_pan", 0.0),
            current_pos.get("shoulder_lift", -30.0),
            current_pos.get("elbow_flex", 0.0),  # 使用当前位置，避免过载
            current_pos.get("wrist_flex", 0.0),
            current_pos.get("wrist_roll", 0.0),
            current_pos.get("gripper", 50.0)
        ]
        
        # 只移动正常的舵机
        print("\n[步骤3] 移动正常舵机...")
        safe_positions = {
            "shoulder_pan": 0.0,
            "shoulder_lift": -30.0,
            "wrist_flex": 0.0,
            "gripper": 50.0
        }
        # 不移动 elbow_flex 和 wrist_roll（可能有问题）
        
        try:
            robot.bus.sync_write("Goal_Position", safe_positions)
            print(f"安全位置: {safe_positions}")
            time.sleep(2)
        except Exception as e:
            print(f"[WARN] 移动时出错: {e}")
        
        # 当前选中的关节
        selected_joint = 0
        angle_step = 5.0
        
        # 加载已保存的姿态
        poses = load_poses()
        
        print("\n[OK] 初始化完成，开始控制...")
        print_help()
        
        # 键盘输入处理
        with KeyboardInput() as kb:
            running = True
            while running:
                print_status(angles, selected_joint, angle_step)
                
                if kb.kbhit():
                    key = kb.getch()
                    
                    # ESC 退出
                    if key == '\x1b':
                        print("\n[INFO] 用户退出")
                        running = False
                    
                    # 数字键选择关节
                    elif key in '123456':
                        selected_joint = int(key) - 1
                        print(f"\n[INFO] 选中关节: {selected_joint + 1}. {JOINT_NAMES[selected_joint]}")
                    
                    # W 或 上箭头：增加角度
                    elif key in 'wW':
                        angles[selected_joint] = min(angles[selected_joint] + angle_step, JOINT_MAX[selected_joint])
                    
                    # S 或 下箭头：减小角度
                    elif key in 'sS':
                        angles[selected_joint] = max(angles[selected_joint] - angle_step, JOINT_MIN[selected_joint])
                    
                    # 设置步长
                    elif key in 'tT':
                        angle_step = 1.0
                        print(f"\n[INFO] 步长改为 {angle_step}°")
                    elif key in 'eE':
                        angle_step = 5.0
                        print(f"\n[INFO] 步长改为 {angle_step}°")
                    elif key in 'rR':
                        angle_step = 10.0
                        print(f"\n[INFO] 步长改为 {angle_step}°")
                    
                    # 显示帮助
                    elif key in 'hH':
                        print_help()
                    
                    # 归位
                    elif key in 'zZ':
                        angles = [-3.5, -62.9, 0.0, -0.1, -3.2, 6.9]
                        print("\n[INFO] 归位到安全位置")
                    
                    # 记录姿态
                    elif key == ' ':
                        pose_name = f"Pose_{len(poses)+1}"
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        pose = {
                            "name": pose_name,
                            "timestamp": timestamp,
                            "angles": {name: angles[i] for i, name in enumerate(JOINT_NAMES)}
                        }
                        poses.append(pose)
                        save_poses(poses)
                        print(f"\n[INFO] 已记录姿态: {pose_name}")
                    
                    # 列出姿态
                    elif key in 'lL':
                        print("\n" + "="*70)
                        print("姿态列表")
                        print("="*70)
                        print_poses(poses)
                        print("\n按任意键继续...")
                        # 等待用户按键，暂停刷新
                        while not kb.kbhit():
                            time.sleep(0.1)
                        kb.getch()  # 清除按键

                    # 分析姿态
                    elif key in 'aA':
                        print("\n" + "="*70)
                        print("姿态差异分析")
                        print("="*70)
                        analyze_poses(poses)
                        print("\n按任意键继续...")
                        # 等待用户按键，暂停刷新
                        while not kb.kbhit():
                            time.sleep(0.1)
                        kb.getch()  # 清除按键

                    # 播放/加载姿态
                    elif key in 'pP':
                        if not poses:
                            print("\n[INFO] 暂无记录的姿态")
                        else:
                            # 显示姿态列表
                            print("\n" + "="*70)
                            print(f"已记录的姿态 (共 {len(poses)} 个)")
                            print("="*70)
                            for i, pose in enumerate(poses):
                                print(f"{i+1}. {pose['name']} - {pose['timestamp']}")
                            print("="*70)
                            print("输入姿态编号 (1-{}) 或按 ESC 取消:".format(len(poses)))

                            # 等待用户输入编号
                            input_str = ""
                            while True:
                                if kb.kbhit():
                                    ch = kb.getch()
                                    # ESC 取消
                                    if ch == '\x1b':
                                        print("\n[INFO] 取消加载姿态")
                                        break
                                    # 回车确认
                                    elif ch == '\n' or ch == '\r':
                                        if input_str:
                                            try:
                                                pose_num = int(input_str)
                                                if 1 <= pose_num <= len(poses):
                                                    selected_pose = poses[pose_num - 1]
                                                    print(f"\n[INFO] 正在加载姿态: {selected_pose['name']}")

                                                    # 更新角度数组
                                                    for i, name in enumerate(JOINT_NAMES):
                                                        angles[i] = selected_pose['angles'][name]

                                                    print("[OK] 姿态已加载，机械臂正在移动...")
                                                else:
                                                    print(f"\n[WARN] 无效编号: {pose_num}")
                                            except ValueError:
                                                print(f"\n[WARN] 无效输入: {input_str}")
                                        break
                                    # 数字输入
                                    elif ch.isdigit():
                                        input_str += ch
                                        print(ch, end='', flush=True)
                                time.sleep(0.05)

                    # 清除过载错误
                    elif key in 'cC':
                        clear_overload_error(robot, JOINT_NAMES)
                
                # 发送当前角度到机械臂
                goal_positions = {name: float(angles[i]) for i, name in enumerate(JOINT_NAMES)}
                robot.bus.sync_write("Goal_Position", goal_positions)
                
                time.sleep(0.05)
        
        # 归位（慢速）
        print("\n[INFO] 归位中（慢速）...")
        try:
            # 目标归位位置（Pose_2）
            goal_positions = {
                "shoulder_pan": -3.5,
                "shoulder_lift": -62.9,
                "elbow_flex": 0.0,
                "wrist_flex": -0.1,
                "wrist_roll": -3.2,
                "gripper": 6.9
            }

            # 分3步移动，每步等待1.5秒
            for i in range(3):
                step_positions = {k: v * (i + 1) / 3 for k, v in goal_positions.items()}
                robot.bus.sync_write("Goal_Position", step_positions)
                print(f"  步骤 {i+1}/3: {[f'{v:.1f}' for v in step_positions.values()]}")
                time.sleep(1.5)

            print("[OK] 归位完成")
        except Exception as e:
            print(f"[WARN] 归位时出错: {e}")
        
        # 断开连接（忽略过载错误）
        try:
            robot.disconnect()
        except RuntimeError as e:
            if "Overload" in str(e):
                print("[WARN] 舵机过载保护触发，强制关闭连接")
            else:
                raise
        
        print("[OK] 程序退出")
        
    except Exception as e:
        print(f"\n[ERROR] 程序失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()