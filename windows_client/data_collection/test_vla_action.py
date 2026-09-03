"""测试VLA动作数据格式"""
import msgpack
import websockets.sync.client
import numpy as np
import cv2
import time
import ssl

SERVER_WS_URL = "wss://8003-cpod-1swd4oph4qxh.pod.compshare.cn"

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

print("="*60)
print("VLA动作数据格式测试")
print("="*60)

try:
    # 连接服务器
    print("\n[步骤1] 连接VLA服务器...")
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED

    ws = websockets.sync.client.connect(
        SERVER_WS_URL,
        timeout=15,
        ssl=ssl_context,
        ping_interval=60,
        ping_timeout=120
    )
    print("[OK] 连接成功")

    # 打开摄像头
    print("\n[步骤2] 打开摄像头...")
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    ret, bgr_frame = cap.read()
    if not ret:
        print("[ERROR] 摄像头读取失败")
        exit(1)

    rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
    print("[OK] 摄像头正常")

    # 发送推理请求
    print("\n[步骤3] 发送推理请求...")
    import msgpack_numpy

    obs_payload = {
        "observation.images.front": rgb_frame,
        "observation.images.side": rgb_frame,
        "observation.state": np.zeros(14, dtype=np.float32),
        "task": "抓取桌面上的蓝色方块",
        "timestamp": time.time()
    }

    packed_data = msgpack_numpy.packb(obs_payload)
    ws.send(packed_data)
    print(f"[OK] 已发送 {len(packed_data)} 字节")

    # 接收响应
    print("\n[步骤4] 接收响应...")
    resp_raw = ws.recv()
    print(f"[OK] 收到 {len(resp_raw)} 字节")

    # 解析动作数据
    print("\n[步骤5] 解析动作数据...")
    action_data = msgpack.unpackb(resp_raw, object_hook=ndarray_unpack)

    print(f"\n动作数据类型: {type(action_data)}")
    print(f"动作数据键: {list(action_data.keys())}")

    # 检查shape
    if b'shape' in action_data:
        shape = action_data[b'shape']
        print(f"动作形状: {shape}")
        print(f"动作类型: {action_data.get(b'type')}")

        # 提取数据
        if b'data' in action_data:
            action_bytes = action_data[b'data']
            action_array = np.frombuffer(action_bytes, dtype=np.float32).reshape(shape)
            print(f"\n动作数组形状: {action_array.shape}")
            print(f"动作数组范围: [{action_array.min():.3f}, {action_array.max():.3f}]")
            print(f"第一个时间步的动作: {action_array[0]}")

            # 检查是否是[25, 14]双臂格式
            if shape[1] == 14:
                print("\n[!] 这是双臂格式！需要提取单臂动作（前6维）")
                right_arm = action_array[0, :6]  # 右臂
                left_arm = action_array[0, 6:12]  # 左臂
                gripper = action_array[0, 12:14]  # 夹爪
                print(f"右臂动作: {right_arm}")
                print(f"左臂动作: {left_arm}")
                print(f"夹爪动作: {gripper}")

    cap.release()
    ws.close()

    print("\n[OK] 测试完成")

except Exception as e:
    print(f"\n[ERROR] 测试失败: {e}")
    import traceback
    traceback.print_exc()