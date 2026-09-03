"""简化版：VLA推理 + 机械臂直接控制（跳过握手初始化）"""
import msgpack
import websockets.sync.client
import numpy as np
import cv2
import time
import ssl
import msgpack_numpy

# 配置
SERVER_WS_URL = "wss://8003-cpod-1swd4oph4qxh.pod.compshare.cn"
SOARM_PORT = "COM3"

def ndarray_unpack(obj):
    if isinstance(obj, dict):
        has_ndarray = "__ndarray__" in obj or b"__ndarray__" in obj
        if has_ndarray:
            try:
                data = obj.get("data") or obj.get(b"data")
                dtype = obj.get("dtype") or obj.get(b"dtype")
                shape = obj.get("shape") or obj.get(b"shape")
                if data and dtype and shape:
                    return np.frombuffer(data, dtype=dtype).reshape(shape)
            except:
                pass
    return obj

print("="*60)
print("VLA + 机械臂控制测试（简化版）")
print("="*60)

# 1. 连接VLA服务器
print("\n[步骤1] 连接VLA服务器...")
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED
ws = websockets.sync.client.connect(SERVER_WS_URL, timeout=15, ssl=ssl_context, ping_interval=60, ping_timeout=120)
print("[OK] VLA服务器连接成功")

# 2. 连接机械臂
print("\n[步骤2] 连接机械臂...")
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

config = SOFollowerRobotConfig(port=SOARM_PORT)
robot = SOFollower(config)
robot.connect()
print("[OK] 机械臂连接成功")

# 读取当前位置
current_pos = robot.bus.sync_read("Present_Position")
print(f"当前位置: {current_pos}")

# 3. 打开摄像头
print("\n[步骤3] 打开摄像头...")
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
print("[OK] 摄像头已打开")

print("\n开始实时控制...")
print("提示：将手放在摄像头前，观察机械臂是否响应")
print("按ESC键退出\n")

try:
    while True:
        # 读取摄像头
        ret, bgr_frame = cap.read()
        if not ret:
            print("[ERROR] 摄像头读取失败")
            break

        rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)

        # 显示画面
        cv2.imshow('VLA Control', bgr_frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

        # VLA推理
        start_time = time.time()
        obs_payload = {
            "observation.images.front": rgb_frame,
            "observation.images.side": rgb_frame,
            "observation.state": np.zeros(14, dtype=np.float32),
            "task": "抓取桌面上的蓝色方块",
            "timestamp": time.time()
        }

        packed_data = msgpack_numpy.packb(obs_payload)
        ws.send(packed_data)
        resp_raw = ws.recv()

        # 解析动作
        action_data = msgpack.unpackb(resp_raw, object_hook=ndarray_unpack)
        infer_ms = (time.time() - start_time) * 1000

        if b'data' in action_data:
            action_bytes = action_data[b'data']
            action_shape = action_data[b'shape']
            action_array = np.frombuffer(action_bytes, dtype=np.float32).reshape(action_shape)

            # 取第一个时间步
            robot_action_6d = action_array[0]

            # 发送到机械臂（使用底层API）
            goal_positions = {
                "shoulder_pan": float(robot_action_6d[0] * 180.0),
                "shoulder_lift": float(robot_action_6d[1] * 90.0),
                "elbow_flex": float(robot_action_6d[2] * 90.0),
                "wrist_flex": float(robot_action_6d[3] * 90.0),
                "wrist_roll": float(robot_action_6d[4] * 90.0),
                "gripper": float(robot_action_6d[5] * 50.0 + 50.0)
            }

            robot.bus.sync_write("Goal_Position", goal_positions)
            print(f"[OK] 推理{infer_ms:.0f}ms | 动作: {robot_action_6d}")

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\n[INFO] 用户中断")
finally:
    cap.release()
    cv2.destroyAllWindows()
    robot.disconnect()
    ws.close()
    print("[INFO] 程序已退出")