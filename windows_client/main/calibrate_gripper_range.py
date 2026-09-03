"""
交互式校准夹爪角度范围
找出夹爪的物理最小和最大位置
"""

import json
import time
from datetime import datetime
from pathlib import Path
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

def calibrate_gripper_range():
    """交互式校准夹爪角度范围""