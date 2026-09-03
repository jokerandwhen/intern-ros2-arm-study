"""多线程版本：VLA推理 + 机械臂控制（流畅显示）"""
import msgpack
import websockets.sync.client
import numpy as np
import cv2
import time
import ssl
import threading
import queue
import msgpack_numpy
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig

# ==================== 配置参数 ====================
SERVER_WS_URL = "wss://8003-cpod-1swd4oph4qxh.pod.compshare.cn"
SOARM_PORT = "COM3"
CAMERA_INDEX = 0

# 机械臂安全参数（角度）
JOINT_MIN = np.array([-180.0, -90.0, -135.0, -90.0, -180.0, 0.0])
JOINT_MAX = np.array([180.0, 90.0, 135.0, 90.0, 180.0, 100.0])
HOME_POSITION = np.array([0.0, 0.0, 45.0, 0.0, 0.0, 50.0])
# ================================================

def ndarray_unpack(obj):
    """反序列化numpy数组"""
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

class VLAController:
    """VLA推理线程"""
    def __init__(self, frame_queue, action_queue, stop_event):
        self.frame_queue = frame_queue
        self.action_queue = action_queue
        self.stop_event = stop_event
        self.ws = None
        self.robot = None
        self.prev_action = None

        # 统计信息
        self.infer_count = 0
        self.total_infer_time = 0

    def connect(self):
        """连接VLA服务器和机械臂"""
        print("[VLA线程] 正在连接服务器...")
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        self.ws = websockets.sync.client.connect(
            SERVER_WS_URL, timeout=15, ssl=ssl_context, ping_interval=60, ping_timeout=120
        )
        print("[VLA线程] VLA服务器连接成功")

        print("[VLA线程] 正在连接机械臂...")
        config = SOFollowerRobotConfig(port=SOARM_PORT)
        self.robot = SOFollower(config)
        self.robot.connect()
        print("[VLA线程] 机械臂连接成功")

        # 归位
        print("[VLA线程] 正在归位...")
        goal_positions = {
            "shoulder_pan": float(HOME_POSITION[0]),
            "shoulder_lift": float(HOME_POSITION[1]),
            "elbow_flex": float(HOME_POSITION[2]),
            "wrist_flex": float(HOME_POSITION[3]),
            "wrist_roll": float(HOME_POSITION[4]),
            "gripper": float(HOME_POSITION[5])
        }
        self.robot.bus.sync_write("Goal_Position", goal_positions)
        time.sleep(1)
        print("[VLA线程] 归位完成")

    def disconnect(self):
        """断开连接"""
        if self.robot:
            self.robot.bus.sync_write("Goal_Position", {
                "shoulder_pan": float(HOME_POSITION[0]),
                "shoulder_lift": float(HOME_POSITION[1]),
                "elbow_flex": float(HOME_POSITION[2]),
                "wrist_flex": float(HOME_POSITION[3]),
                "wrist_roll": float(HOME_POSITION[4]),
                "gripper": float(HOME_POSITION[5])
            })
            time.sleep(0.5)
            self.robot.disconnect()
            print("[VLA线程] 机械臂已断开")

        if self.ws:
            self.ws.close()
            print("[VLA线程] VLA服务器已断开")

    def run(self):
        """主循环"""
        try:
            self.connect()

            while not self.stop_event.is_set():
                # 从队列获取最新帧
                try:
                    frame_data = self.frame_queue.get(timeout=0.1)
                    rgb_frame, timestamp = frame_data
                except queue.Empty:
                    continue

                # VLA推理
                infer_start = time.time()
                obs_payload = {
                    "observation.images.front": rgb_frame,
                    "observation.images.side": rgb_frame,
                    "observation.state": np.zeros(14, dtype=np.float32),
                    "task": "抓取桌面上的蓝色方块",
                    "timestamp": timestamp
                }

                packed_data = msgpack_numpy.packb(obs_payload)
                self.ws.send(packed_data)
                resp_raw = self.ws.recv()

                # 解析动作
                action_data = msgpack.unpackb(resp_raw, object_hook=ndarray_unpack)

                if 'action' in action_data:
                    action_raw = action_data['action']
                    if isinstance(action_raw, dict) and b'data' in action_raw:
                        action_bytes = action_raw[b'data']
                        action_shape = action_raw[b'shape']
                        action_array = np.frombuffer(action_bytes, dtype=np.float32).reshape(action_shape)
                        robot_action_6d = action_array[0]

                        # 安全限幅
                        robot_action_6d = np.clip(robot_action_6d, JOINT_MIN, JOINT_MAX)

                        # 发送到机械臂
                        goal_positions = {
                            "shoulder_pan": float(robot_action_6d[0]),
                            "shoulder_lift": float(robot_action_6d[1]),
                            "elbow_flex": float(robot_action_6d[2]),
                            "wrist_flex": float(robot_action_6d[3]),
                            "wrist_roll": float(robot_action_6d[4]),
                            "gripper": float(robot_action_6d[5])
                        }
                        self.robot.bus.sync_write("Goal_Position", goal_positions)

                        # 统计
                        infer_time = (time.time() - infer_start) * 1000
                        self.infer_count += 1
                        self.total_infer_time += infer_time
                        avg_infer_time = self.total_infer_time / self.infer_count

                        # 发送动作到显示队列
                        try:
                            self.action_queue.put_nowait((robot_action_6d, infer_time, avg_infer_time))
                        except queue.Full:
                            pass

        except Exception as e:
            print(f"[VLA线程] 错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.disconnect()

def main():
    print("="*60)
    print("多线程版本 - VLA + 机械臂控制（流畅显示）")
    print("="*60)

    # 创建队列和事件
    frame_queue = queue.Queue(maxsize=2)  # 图像帧队列
    action_queue = queue.Queue(maxsize=2)  # 动作队列
    stop_event = threading.Event()

    # 创建VLA线程
    vla_controller = VLAController(frame_queue, action_queue, stop_event)
    vla_thread = threading.Thread(target=vla_controller.run, daemon=True)

    # 打开摄像头
    print("\n[主线程] 正在打开摄像头...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print("[主线程] 摄像头已打开")

    # 启动VLA线程
    vla_thread.start()
    print("[主线程] VLA线程已启动")

    print("\n开始运行...")
    print("摄像头画面将实时显示")
    print("按ESC键退出\n")

    try:
        # 统计FPS
        fps_start_time = time.time()
        fps_frame_count = 0
        fps = 0

        while True:
            # 读取摄像头
            ret, bgr_frame = cap.read()
            if not ret:
                print("[主线程] 摄像头读取失败")
                break

            # 发送帧到VLA线程（非阻塞）
            try:
                rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
                frame_queue.put_nowait((rgb_frame, time.time()))
            except queue.Full:
                pass  # 队列满，跳过

            # 获取动作信息（非阻塞）
            try:
                action_data = action_queue.get_nowait()
                robot_action, infer_time, avg_infer_time = action_data

                # 在画面上显示信息
                cv2.putText(bgr_frame, f"Infer: {infer_time:.0f}ms", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(bgr_frame, f"FPS: {fps:.1f}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(bgr_frame, f"Action: {robot_action[:3]}", (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            except queue.Empty:
                pass

            # 计算FPS
            fps_frame_count += 1
            if time.time() - fps_start_time >= 1.0:
                fps = fps_frame_count / (time.time() - fps_start_time)
                fps_frame_count = 0
                fps_start_time = time.time()

            # 显示画面
            cv2.imshow('VLA Control (Multi-thread)', bgr_frame)

            # 按ESC退出
            if cv2.waitKey(1) & 0xFF == 27:
                break

    except KeyboardInterrupt:
        print("\n[主线程] 用户中断")
    finally:
        print("[主线程] 正在退出...")
        stop_event.set()
        vla_thread.join(timeout=2)
        cap.release()
        cv2.destroyAllWindows()
        print("[主线程] 程序已退出")

if __name__ == "__main__":
    main()