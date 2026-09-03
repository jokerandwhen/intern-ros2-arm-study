import msgpack
import websockets.sync.client
import numpy as np
import cv2
import time
import ssl
from typing import Dict, Any

# ===================== 配置区（修改这里适配你的服务器）=====================
# 优云智算华北C无独立公网GPU容器：
#   - 容器内置GPU算力，无需额外购买云服务器，可直接运行VLA推理
#   - 通过容器代理wss://域名访问，支持SSL加密传输
#   - 本地摄像头采集图像 -> 远程容器VLA推理 -> 返回机器人动作指令
SERVER_WS_URL = "wss://8003-cpod-1swd4oph4qxh.pod.compshare.cn"  # 优云智算容器代理（wss加密）

# 有公网IP的云服务器配置示例（不使用容器代理时）：
# SERVER_WS_URL = "ws://你的云服务器公网IP:8003"  # 自有服务器直连（ws非加密）

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_INDEX = 0         # 摄像头索引（None=自动检测机械臂摄像头，或手动指定：0, 1, 2...）

# WebSocket连接参数
WS_CONNECT_TIMEOUT = 15  # 连接超时（秒）
WS_RECONNECT_DELAY = 3   # 断线重连延迟（秒）

# SoArm101机械臂配置
SOARM_PORT = "COM3"      # Windows串口号（根据实际情况修改，如COM3、COM4等）
                         # Linux/Mac: "/dev/ttyUSB0" 或 "/dev/ttyACM0"
USE_ROBOT = True        # 是否启用机械臂控制（False则仅测试VLA推理）
# ==========================================================================

# ===================== 机械臂安全参数 =====================
# 角度限制（单位：度）
JOINT_MIN = np.array([-180.0, -90.0, -135.0, -90.0, -180.0, 0.0])    # 关节下限（角度）
JOINT_MAX = np.array([180.0, 90.0, 135.0, 90.0, 180.0, 100.0])        # 关节上限（角度）
JOINT_VELOCITY_LIMIT = 180.0  # 单步最大角度变化量（取消限制）
HOME_POSITION = np.array([0.0, 0.0, 45.0, 0.0, 0.0, 50.0])            # 归位位置（角度）
MAX_RECONNECT_ATTEMPTS = 3   # 最大重连次数
# ====================================================================

def clamp_action(action: np.ndarray, prev_action: np.ndarray = None) -> np.ndarray:
    """
    动作限幅和速度约束（防止堵电机）- 角度版本
    :param action: 目标动作（6维，角度值）
    :param prev_action: 上一步动作（用于速度限制）
    :return: 安全限幅后的动作（角度值）
    """
    # 1. 关节限幅（角度）
    action = np.clip(action, JOINT_MIN, JOINT_MAX)

    # 2. 速度限制（单步角度变化不能太大，防止堵电机）
    if prev_action is not None:
        delta = action - prev_action
        delta = np.clip(delta, -JOINT_VELOCITY_LIMIT, JOINT_VELOCITY_LIMIT)
        action = prev_action + delta

    return action

def robot_handshake(robot) -> bool:
    """
    机械臂握手初始化（归位到安全位置）
    :param robot: SOFollower实例
    :return: 是否成功
    """
    try:
        print("[INFO] 正在执行机械臂握手初始化...")

        # 分步归位，避免突然运动
        steps = 10
        current_pos = np.zeros(6)  # 假设初始位置为0

        for i in range(steps):
            # 渐进移动到归位位置
            target = current_pos + (HOME_POSITION - current_pos) * (i + 1) / steps
            target = clamp_action(target, current_pos)

            # 发送动作（使用底层sync_write避免bug）
            # 直接发送角度值
            goal_positions = {
                "shoulder_pan": float(target[0]),
                "shoulder_lift": float(target[1]),
                "elbow_flex": float(target[2]),
                "wrist_flex": float(target[3]),
                "wrist_roll": float(target[4]),
                "gripper": float(target[5])
            }
            robot.bus.sync_write("Goal_Position", goal_positions)

            current_pos = target
            time.sleep(0.2)  # 每步等待200ms

        print("[OK] 机械臂握手初始化完成，已归位到安全位置")
        return True

    except Exception as e:
        print(f"[ERROR] 机械臂握手初始化失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def connect_robot_with_retry(port: str, max_attempts: int = MAX_RECONNECT_ATTEMPTS):
    """
    机械臂连接（带重试机制）
    :param port: 串口号
    :param max_attempts: 最大重试次数
    :return: robot实例或None
    """
    for attempt in range(1, max_attempts + 1):
        try:
            from lerobot.robots.so_follower.so_follower import SOFollower
            from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
            
            print(f"[INFO] 尝试连接SoArm101（第{attempt}次，端口：{port}）...")
            config = SOFollowerRobotConfig(port=port)
            robot = SOFollower(config)
            robot.connect()
            
            print("[OK] SoArm101连接成功")
            return robot
            
        except Exception as e:
            print(f"[WARN] 第{attempt}次连接失败：{e}")
            if attempt < max_attempts:
                print(f"       3秒后重试...")
                time.sleep(3)
    
    print(f"[ERROR] 机械臂连接失败，已尝试{max_attempts}次")
    return None

def ndarray_pack(obj: Any) -> Any:
    """序列化numpy图像数组，适配LingBot-VLA msgpack协议（支持递归）"""
    if isinstance(obj, np.ndarray):
        return {
            "__ndarray__": True,
            "data": obj.tobytes(),
            "dtype": obj.dtype.str,
            "shape": obj.shape
        }
    elif isinstance(obj, dict):
        # 递归处理字典
        return {k: ndarray_pack(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        # 递归处理列表和元组
        return [ndarray_pack(item) for item in obj]
    return obj

def ndarray_unpack(obj: Any) -> Any:
    """反序列化numpy数组（支持字符串和bytes键）"""
    if isinstance(obj, dict):
        # 支持字符串键和bytes键
        has_ndarray = "__ndarray__" in obj or b"__ndarray__" in obj
        if has_ndarray:
            # 尝试获取数据，兼容字符串和bytes键
            try:
                data = obj.get("data") or obj.get(b"data")
                dtype = obj.get("dtype") or obj.get(b"dtype")
                shape = obj.get("shape") or obj.get(b"shape")
                if data and dtype and shape:
                    return np.frombuffer(data, dtype=dtype).reshape(shape)
            except:
                pass
    return obj

class LingBotVLAClient:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws = None
        self.packer = msgpack.Packer(default=ndarray_pack)
        self.connected = False

    def connect(self):
        """连接远程VLA推理服务，支持wss证书校验和连接超时"""
        try:
            # 创建SSL上下文（用于wss加密连接）
            ssl_context = None
            if self.ws_url.startswith("wss://"):
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = True
                ssl_context.verify_mode = ssl.CERT_REQUIRED

            # 建立WebSocket连接（15秒超时）
            # 增加ping间隔和超时，适应GPU推理时间
            self.ws = websockets.sync.client.connect(
                self.ws_url,
                timeout=WS_CONNECT_TIMEOUT,
                ssl=ssl_context,
                ping_interval=60,  # 每60秒发送ping
                ping_timeout=120   # 120秒内必须收到pong响应
            )

            # 接收模型元信息
            meta_raw = self.ws.recv()
            # 确保是bytes类型
            if isinstance(meta_raw, str):
                meta_raw = meta_raw.encode('utf-8')
            self.meta = msgpack.unpackb(meta_raw, object_hook=ndarray_unpack)
            self.connected = True
            print(f"[OK] 连接LingBot-VLA服务成功，模型元信息：{self.meta}")

        except Exception as e:
            self.connected = False
            print(f"[ERROR] 连接失败：{e}")
            raise

    def reconnect(self):
        """断线自动重连机制"""
        print(f"[WARN] 连接已断开，{WS_RECONNECT_DELAY}秒后尝试重连...")
        time.sleep(WS_RECONNECT_DELAY)

        # 关闭旧连接
        if self.ws:
            try:
                self.ws.close()
            except:
                pass

        # 尝试重新连接
        try:
            self.connect()
            print("[OK] 重连成功")
        except Exception as e:
            print(f"[ERROR] 重连失败：{e}")
            self.connected = False

    def infer(self, rgb_image: np.ndarray, task_text: str = "") -> Dict[str, Any]:
        """
        单次视觉推理（支持断线自动重连）
        :param rgb_image: np.ndarray HWC RGB图像
        :param task_text: 自然语言指令，如"拿起水杯放到右边"
        :return: dict{"action":机械臂动作数组, "server_timing":推理耗时}
        """
        # 检查连接状态，断线则自动重连
        if not self.connected or self.ws is None:
            self.reconnect()

        try:
            # 使用msgpack-numpy自动序列化numpy数组
            import msgpack_numpy
            
            # RoboTwin需要多个摄像头和机器人状态
            # 根据服务器要求，使用正确的字段名
            obs_payload = {
                "observation.images.front": rgb_image,  # 正面摄像头（主要视角）
                "observation.images.side": rgb_image,   # 侧面摄像头（辅助视角）
                "observation.state": np.zeros(14, dtype=np.float32),  # 机器人关节状态（14维双臂）
                "task": task_text,  # 任务指令
                "timestamp": time.time()
            }

            # 使用msgpack_numpy序列化
            packed_data = msgpack_numpy.packb(obs_payload)
            print(f"[DEBUG] 发送数据大小: {len(packed_data)} 字节")
            self.ws.send(packed_data)
            # 接收模型输出动作
            resp_raw = self.ws.recv()
            # 确保是bytes类型
            if isinstance(resp_raw, str):
                resp_raw = resp_raw.encode('utf-8')

            # 调试：打印原始数据
            print(f"[DEBUG] 接收到的数据长度: {len(resp_raw)}, 类型: {type(resp_raw)}")

            # 检查是否是错误信息（Python Traceback）
            if resp_raw.startswith(b'Traceback'):
                error_msg = resp_raw.decode('utf-8')
                print(f"[ERROR] 服务器返回错误:\n{error_msg}")
                raise Exception("服务器推理失败，请检查服务器日志")

            try:
                action_data = msgpack.unpackb(resp_raw, object_hook=ndarray_unpack)
            except Exception as e:
                print(f"[ERROR] msgpack解析失败: {e}")
                print(f"[DEBUG] 数据前100字节: {resp_raw[:100]}")
                raise

            return action_data

        except Exception as e:
            print(f"[ERROR] 推理过程发生错误：{e}")
            # 标记为断线，下次调用时自动重连
            self.connected = False
            raise

    def close(self):
        """关闭连接"""
        self.connected = False
        if self.ws:
            self.ws.close()
            print("[INFO] 断开VLA服务连接")

# ---------------------- 摄像头检测与选择 ----------------------
def detect_cameras():
    """检测系统中所有可用的摄像头"""
    cameras = []
    for i in range(10):  # 尝试0-9号摄像头
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                cameras.append({
                    'index': i,
                    'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    'name': f'摄像头 {i}'
                })
            cap.release()
    return cameras

def select_camera():
    """选择摄像头（优先选择机械臂摄像头）"""
    if CAMERA_INDEX is not None:
        print(f"[INFO] 使用指定的摄像头索引：{CAMERA_INDEX}")
        return CAMERA_INDEX
    
    cameras = detect_cameras()
    if not cameras:
        print("[ERROR] 未检测到任何摄像头")
        return 0
    
    print(f"\n[INFO] 检测到 {len(cameras)} 个摄像头：")
    for cam in cameras:
        print(f"  [{cam['index']}] {cam['name']} ({cam['width']}x{cam['height']})")
    
    # 如果只有一个摄像头，直接使用
    if len(cameras) == 1:
        print(f"[INFO] 自动选择摄像头 {cameras[0]['index']}")
        return cameras[0]['index']
    
    # 多个摄像头时，让用户选择
    print("\n请选择机械臂摄像头：")
    print("提示：机械臂摄像头通常是外接USB摄像头")
    print("输入摄像头索引（0-9），或按Enter使用默认摄像头0")
    
    try:
        # 在非交互模式下，默认使用第一个外接摄像头（通常是机械臂摄像头）
        # 笔记本自带摄像头通常是索引0，外接摄像头是索引1或更大
        external_cameras = [c for c in cameras if c['index'] > 0]
        if external_cameras:
            selected = external_cameras[0]['index']
            print(f"[INFO] 自动选择外接摄像头 {selected}（可能是机械臂摄像头）")
            return selected
        else:
            print("[INFO] 使用默认摄像头 0")
            return 0
    except:
        print("[INFO] 使用默认摄像头 0")
        return 0

# ---------------------- 机器人主循环示例（SoArm101机械臂调用入口）----------------------
def robot_main_loop():
    # 1. 初始化VLA客户端
    client = LingBotVLAClient(SERVER_WS_URL)
    client.connect()

    # 2. 初始化SoArm101机械臂（带重试和握手）
    robot = None
    prev_action = None  # 上一步动作（用于速度限制）
    
    if USE_ROBOT:
        robot = connect_robot_with_retry(SOARM_PORT)
        if robot:
            # 执行握手初始化（归位）
            if not robot_handshake(robot):
                print("[WARN] 握手初始化失败，继续运行但不保证安全")
        else:
            print("[WARN] 机械臂连接失败，继续运行VLA推理但不控制机械臂")

    # 3. 打开机械臂摄像头（自动检测或手动指定）
    camera_index = select_camera()
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    task_instruction = "抓取桌面上的蓝色方块放到收纳盒"

    try:
        while True:
            ret, bgr_frame = cap.read()
            if not ret:
                print("[ERROR] 摄像头读取失败")
                break

            # BGR转RGB（VLA模型输入要求RGB格式）
            rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)

            # 显示摄像头画面
            cv2.imshow('SoArm101 Camera', bgr_frame)
            # 按ESC键退出
            if cv2.waitKey(1) & 0xFF == 27:
                break

            # 调用远程GPU模型推理
            start_time = time.time()
            action_dict = client.infer(rgb_frame, task_text=task_instruction)
            infer_ms = (time.time() - start_time) * 1000

            # 解析动作数据（减少调试输出）
            # 提取动作数据 - 兼容两种格式
            if 'action' in action_dict:
                # 新格式：字符串键
                action_raw = action_dict['action']
                print(f"[DEBUG] action类型: {type(action_raw)}")

                # 检查是否是numpy数组
                if isinstance(action_raw, np.ndarray):
                    # 如果是多维数组，取第一个时间步
                    if len(action_raw.shape) == 2:
                        robot_action_6d = action_raw[0]
                    else:
                        robot_action_6d = action_raw
                    print(f"[INFO] 推理耗时{infer_ms:.1f}ms，动作值：{robot_action_6d}")

                # 检查是否是字典（包含ndarray）
                elif isinstance(action_raw, dict):
                    # 尝试提取numpy数组
                    if b'data' in action_raw:
                        action_bytes = action_raw[b'data']
                        action_shape = action_raw[b'shape']
                        action_array = np.frombuffer(action_bytes, dtype=np.float32).reshape(action_shape)
                        robot_action_6d = action_array[0]
                        print(f"[INFO] 推理耗时{infer_ms:.1f}ms，动作值：{robot_action_6d}")
                    else:
                        print(f"[WARN] action字典格式未知: {list(action_raw.keys())}")
                        robot_action_6d = np.zeros(6, dtype=np.float32)
                else:
                    print(f"[WARN] action类型未知: {type(action_raw)}")
                    robot_action_6d = np.zeros(6, dtype=np.float32)

            elif b'data' in action_dict:
                # 旧格式：bytes键
                action_bytes = action_dict[b'data']
                action_shape = action_dict[b'shape']
                action_array = np.frombuffer(action_bytes, dtype=np.float32).reshape(action_shape)
                robot_action_6d = action_array[0]
                print(f"[INFO] 推理耗时{infer_ms:.1f}ms，动作值：{robot_action_6d}")
            else:
                # 完全未知格式
                print(f"[WARN] 未识别的数据格式")
                robot_action_6d = np.zeros(6, dtype=np.float32)

            # ===================== SoArm101机械臂控制 =====================
            if robot and USE_ROBOT:
                try:
                    # VLA返回6维动作，直接使用（已经归一化到[-1, 1]）
                    soarm_action_6d = robot_action_6d.copy()

                    # 动作限幅和安全检查
                    soarm_action_6d = clamp_action(soarm_action_6d, prev_action)

                    # 将角度值发送到机械臂（使用底层API）
                    goal_positions = {
                        "shoulder_pan": float(soarm_action_6d[0]),
                        "shoulder_lift": float(soarm_action_6d[1]),
                        "elbow_flex": float(soarm_action_6d[2]),
                        "wrist_flex": float(soarm_action_6d[3]),
                        "wrist_roll": float(soarm_action_6d[4]),
                        "gripper": float(soarm_action_6d[5])
                    }

                    # 发送动作到机械臂（使用底层API）
                    robot.bus.sync_write("Goal_Position", goal_positions)

                    # 更新上一步动作
                    prev_action = soarm_action_6d.copy()

                    print(f"[OK] 动作已发送: {soarm_action_6d}")

                except Exception as e:
                    print(f"[ERROR] 机械臂控制失败：{e}")
                    import traceback
                    traceback.print_exc()
                    # 检测到异常，尝试重连
                    print("[INFO] 尝试重新连接机械臂...")
                    robot = connect_robot_with_retry(SOARM_PORT, max_attempts=1)
                    if robot:
                        robot_handshake(robot)
                    prev_action = None  # 重置动作历史
            # =================================================================

            # 简单延时（避免过快循环）
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[INFO] 用户中断程序")
    except Exception as e:
        print(f"[ERROR] 程序异常退出：{e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()

        # 断开机械臂连接
        if robot:
            try:
                # 回到归位位置（使用底层sync_write，直接发送角度值）
                home_positions = {
                    "shoulder_pan": float(HOME_POSITION[0]),
                    "shoulder_lift": float(HOME_POSITION[1]),
                    "elbow_flex": float(HOME_POSITION[2]),
                    "wrist_flex": float(HOME_POSITION[3]),
                    "wrist_roll": float(HOME_POSITION[4]),
                    "gripper": float(HOME_POSITION[5])
                }
                robot.bus.sync_write("Goal_Position", home_positions)
                time.sleep(1.0)
                robot.disconnect()
                print("[INFO] SoArm101已断开并归位")
            except Exception as e:
                print(f"[WARN] 机械臂断开失败：{e}")

        client.close()

if __name__ == "__main__":
    robot_main_loop()
