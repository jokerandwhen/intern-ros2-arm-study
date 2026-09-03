"""
机械臂抓取控制模块
功能：控制SoArm101从动臂（主臂）进行物体抓取
"""

import time
import numpy as np
from typing import Dict, Tuple, Optional


class ArmController:
    """机械臂控制器"""

    def __init__(self, port: str = "COM3"):
        self.port = port
        self.robot = None
        self.connected = False

        # 安全位置（度）
        self.home_position = {
            'shoulder_pan.pos': 0.0,
            'shoulder_lift.pos': 30.0,
            'elbow_flex.pos': 30.0,
            'wrist_flex.pos': 0.0,
            'wrist_roll.pos': 0.0,
            'gripper.pos': 50.0
        }

        # 抓取位置（度）
        self.grasp_ready = {
            'shoulder_pan.pos': 0.0,
            'shoulder_lift.pos': 50.0,
            'elbow_flex.pos': 60.0,
            'wrist_flex.pos': 30.0,
            'wrist_roll.pos': 0.0,
            'gripper.pos': 80.0  # 打开
        }

        # 关节限幅
        self.limits = {
            'shoulder_pan.pos': (-150, 150),
            'shoulder_lift.pos': (-160, 150),
            'elbow_flex.pos': (-100, 100),
            'wrist_flex.pos': (-100, 100),
            'wrist_roll.pos': (-90, 90),
            'gripper.pos': (0, 100)
        }

    def connect(self) -> bool:
        """连接机械臂"""
        try:
            from lerobot.robots.so_follower.so_follower import SOFollower
            from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

            print(f"[INFO] 正在连接主臂（{self.port}）...")
            config = SOFollowerRobotConfig(port=self.port)
            self.robot = SOFollower(config)
            self.robot.connect(calibrate=False)
            self.connected = True
            print("[OK] 主臂连接成功")
            return True

        except Exception as e:
            print(f"[ERROR] 连接失败: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """断开连接"""
        if self.robot:
            try:
                self.robot.disconnect()
            except:
                pass
        self.connected = False
        print("[INFO] 主臂已断开")

    def clip_position(self, position: Dict) -> Dict:
        """位置限幅"""
        clipped = {}
        for joint, value in position.items():
            if joint in self.limits:
                min_val, max_val = self.limits[joint]
                clipped[joint] = float(np.clip(value, min_val, max_val))
            else:
                clipped[joint] = float(value)
        return clipped

    def send_action(self, position: Dict, smooth: bool = True, steps: int = 20):
        """
        发送动作到机械臂
        :param position: 目标位置（度）
        :param smooth: 是否平滑移动
        :param steps: 平滑移动的步数
        """
        if not self.connected or self.robot is None:
            print("[ERROR] 机械臂未连接")
            return

        # 限幅
        position = self.clip_position(position)

        try:
            if smooth:
                # 平滑移动
                current_obs = self.robot.get_observation()
                start_pos = {k: current_obs.get(k, 0) for k in position.keys()}

                for i in range(1, steps + 1):
                    alpha = i / steps
                    interp_pos = {}
                    for joint in position.keys():
                        start_val = start_pos.get(joint, 0)
                        end_val = position[joint]
                        interp_pos[joint] = start_val + (end_val - start_val) * alpha

                    self.robot.send_action(interp_pos)
                    time.sleep(0.02)
            else:
                self.robot.send_action(position)

        except Exception as e:
            print(f"[ERROR] 发送动作失败: {e}")

    def go_home(self):
        """回到安全位置"""
        print("[INFO] 回到安全位置...")
        self.send_action(self.home_position, smooth=True, steps=30)
        print("[OK] 已回到安全位置")

    def go_grasp_ready(self):
        """移动到抓取准备位置"""
        print("[INFO] 移动到抓取准备位置...")
        self.send_action(self.grasp_ready, smooth=True, steps=30)
        print("[OK] 已到达抓取准备位置")

    def open_gripper(self):
        """打开夹爪"""
        print("[INFO] 打开夹爪...")
        current_obs = self.robot.get_observation()
        position = {k: current_obs.get(k, 0) for k in self.home_position.keys()}
        position['gripper.pos'] = 90.0
        self.send_action(position, smooth=True, steps=10)

    def close_gripper(self):
        """关闭夹爪"""
        print("[INFO] 关闭夹爪...")
        current_obs = self.robot.get_observation()
        position = {k: current_obs.get(k, 0) for k in self.home_position.keys()}
        position['gripper.pos'] = 10.0
        self.send_action(position, smooth=True, steps=10)

    def move_to_target(self, arm_x: float, arm_y: float):
        """
        移动到目标位置（基于视觉坐标）
        :param arm_x: x方向偏移（度）
        :param arm_y: y方向偏移（度）
        """
        current_obs = self.robot.get_observation()
        position = {k: current_obs.get(k, 0) for k in self.home_position.keys()}

        # 调整关节角度
        # arm_x影响shoulder_pan（左右）
        # arm_y影响shoulder_lift和elbow_flex（上下）
        position['shoulder_pan.pos'] += arm_x * 0.5
        position['shoulder_lift.pos'] += arm_y * 0.3
        position['elbow_flex.pos'] += arm_y * 0.3

        print(f"[INFO] 移动到目标位置: x={arm_x:.1f}, y={arm_y:.1f}")
        self.send_action(position, smooth=True, steps=15)

    def grasp_object(self, arm_x: float, arm_y: float):
        """
        完整的抓取流程
        :param arm_x: 目标x坐标
        :param arm_y: 目标y坐标
        """
        print(f"\n[INFO] 开始抓取物体 (x={arm_x:.1f}, y={arm_y:.1f})...")

        # 1. 移动到抓取准备位置
        self.go_grasp_ready()
        time.sleep(0.5)

        # 2. 打开夹爪
        self.open_gripper()
        time.sleep(0.5)

        # 3. 移动到目标位置
        self.move_to_target(arm_x, arm_y)
        time.sleep(0.5)

        # 4. 关闭夹爪
        self.close_gripper()
        time.sleep(1.0)

        # 5. 抬起
        current_obs = self.robot.get_observation()
        position = {k: current_obs.get(k, 0) for k in self.home_position.keys()}
        position['shoulder_lift.pos'] -= 30  # 抬起
        position['elbow_flex.pos'] -= 20
        self.send_action(position, smooth=True, steps=20)
        time.sleep(0.5)

        print("[OK] 抓取完成！")

    def release_object(self):
        """释放物体"""
        print("[INFO] 释放物体...")

        # 1. 移动到释放位置
        current_obs = self.robot.get_observation()
        position = {k: current_obs.get(k, 0) for k in self.home_position.keys()}
        position['shoulder_pan.pos'] = 30  # 移到右侧
        self.send_action(position, smooth=True, steps=20)
        time.sleep(0.5)

        # 2. 放下
        position['shoulder_lift.pos'] = 50
        position['elbow_flex.pos'] = 60
        self.send_action(position, smooth=True, steps=20)
        time.sleep(0.5)

        # 3. 打开夹爪
        self.open_gripper()
        time.sleep(0.5)

        print("[OK] 物体已释放！")
