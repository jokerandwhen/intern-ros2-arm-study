"""
SoArm101 机械臂控制器 - 使用正确的STS3215寄存器
用于单臂位置控制（从动臂COM3）
"""
import serial
import time

class SoArmController:
    # STS3215 权威寄存器地址
    TORQUE_ENABLE = 40
    ACCELERATION = 41
    GOAL_POSITION = 42
    GOAL_SPEED = 46
    TORQUE_LIMIT = 48
    LOCK = 55
    PRESENT_POSITION = 56
    PRESENT_SPEED = 58
    PRESENT_LOAD = 60
    PRESENT_VOLTAGE = 62
    PRESENT_TEMP = 63
    STATUS = 65
    MOVING = 66
    
    MOTOR_NAMES = {1: "shoulder_pan", 2: "shoulder_lift", 3: "elbow_flex", 
                   4: "wrist_flex", 5: "wrist_roll", 6: "gripper"}
    
    def __init__(self, port="COM3", baud=1000000):
        self.port = port
        self.baud = baud
        self.ser = None
    
    def connect(self):
        """连接串口"""
        self.ser = serial.Serial(self.port, baudrate=self.baud, timeout=0.2)
        time.sleep(0.3)
        # 禁用扭矩、设置加速度
        for mid in range(1, 7):
            self._write1(mid, self.TORQUE_ENABLE, 0)
            time.sleep(0.01)
            self._write1(mid, self.ACCELERATION, 254)
            time.sleep(0.01)
        print(f"✓ 已连接 {self.port}")
    
    def disconnect(self):
        """断开连接"""
        if self.ser and self.ser.is_open:
            try:
                for mid in range(1, 7):
                    try:
                        self._write1(mid, self.TORQUE_ENABLE, 0)
                    except:
                        pass
                    time.sleep(0.005)
                self.ser.close()
                print(f"✓ 已断开 {self.port}")
            except:
                try:
                    self.ser.close()
                except:
                    pass
    
    def _build_packet(self, mid, instr, params=b''):
        length = len(params) + 2
        pkt = bytes([0xFF, 0xFF, mid, length, instr]) + params
        cs = (~sum(pkt[2:]) & 0xFF)
        return pkt + bytes([cs])
    
    def _write1(self, mid, addr, val):
        """写1字节"""
        for _ in range(3):
            self.ser.reset_input_buffer()
            self.ser.write(self._build_packet(mid, 0x03, bytes([addr, val & 0xFF])))
            time.sleep(0.015)
            resp = self.ser.read(20)
            if len(resp) >= 4:
                return True
            time.sleep(0.02)
        return False
    
    def _write2(self, mid, addr, val):
        """写2字节（低字节在前）"""
        for _ in range(3):
            self.ser.reset_input_buffer()
            self.ser.write(self._build_packet(mid, 0x03, 
                bytes([addr, val & 0xFF, (val >> 8) & 0xFF])))
            time.sleep(0.015)
            resp = self.ser.read(20)
            if len(resp) >= 4:
                return True
            time.sleep(0.02)
        return False
    
    def _read1(self, mid, addr):
        """读1字节"""
        for _ in range(3):
            self.ser.reset_input_buffer()
            self.ser.write(self._build_packet(mid, 0x02, bytes([addr, 1])))
            time.sleep(0.015)
            r = self.ser.read(64)
            if len(r) >= 6:
                return r[5]
            time.sleep(0.02)
        return None
    
    def _read2(self, mid, addr):
        """读2字节"""
        for _ in range(3):
            self.ser.reset_input_buffer()
            self.ser.write(self._build_packet(mid, 0x02, bytes([addr, 2])))
            time.sleep(0.015)
            r = self.ser.read(64)
            if len(r) >= 7:
                return r[5] | (r[6] << 8)
            time.sleep(0.02)
        return None
    
    def _sync_write_positions(self, positions_dict, speed=None):
        """同步写多电机目标位置"""
        params = bytes([self.GOAL_POSITION, 2])
        for mid, pos in positions_dict.items():
            params += bytes([mid, pos & 0xFF, (pos >> 8) & 0xFF])
        self.ser.reset_input_buffer()
        self.ser.write(self._build_packet(0xFE, 0x83, params))
        time.sleep(0.005)
    
    def ping(self, mid):
        """检测电机是否在线"""
        for _ in range(3):
            self.ser.reset_input_buffer()
            self.ser.write(self._build_packet(mid, 0x01))
            time.sleep(0.03)
            if len(self.ser.read(20)) >= 6:
                return True
            time.sleep(0.02)
        return False
    
    def read_all_positions(self):
        """读取所有电机当前位置"""
        positions = {}
        for mid in range(1, 7):
            pos = self._read2(mid, self.PRESENT_POSITION)
            if pos is not None:
                positions[mid] = pos
            else:
                positions[mid] = 2048
        return positions
    
    def read_all_positions_fast(self):
        """高速读取所有电机位置（read(8)精确读取，读满立即返回）"""
        positions = {}
        for mid in range(1, 7):
            pos = None
            for _ in range(2):  # 最多2次
                self.ser.reset_input_buffer()
                pkt = self._build_packet(mid, 0x02, bytes([self.PRESENT_POSITION, 2]))
                self.ser.write(pkt)
                time.sleep(0.005)  # 等5ms（Windows实际约15ms）让舵机响应
                r = self.ser.read(8)  # 精确读8字节，读满立即返回
                if len(r) >= 8 and r[0] == 0xFF and r[1] == 0xFF:
                    pos = r[5] | (r[6] << 8)
                    break
                # 清除残留
                if self.ser.in_waiting > 0:
                    self.ser.read(self.ser.in_waiting)
            positions[mid] = pos if pos is not None else positions.get(mid-1, 2048)
        return positions
    
    def read_status(self):
        """读取所有电机状态"""
        result = {}
        for mid in range(1, 7):
            status = self._read1(mid, self.STATUS)
            v = self._read1(mid, self.PRESENT_VOLTAGE)
            t = self._read1(mid, self.PRESENT_TEMP)
            result[mid] = {
                'status': status or 0,
                'voltage': (v or 0) / 10.0,
                'temp': t or 0
            }
        return result
    
    def enable_torque(self):
        """使能所有电机扭矩"""
        for mid in range(1, 7):
            self._write2(mid, self.TORQUE_LIMIT, 1023)
            time.sleep(0.01)
            self._write1(mid, self.TORQUE_ENABLE, 1)
            time.sleep(0.01)
        print("✓ 扭矩已使能")
    
    def disable_torque(self):
        """禁用所有电机扭矩"""
        for mid in range(1, 7):
            self._write1(mid, self.TORQUE_ENABLE, 0)
            time.sleep(0.01)
        print("✓ 扭矩已禁用")
    
    def move_to(self, positions, speed=2000, wait=True, wait_time=2.0):
        """移动到指定位置（字典 {motor_id: position}）"""
        # 设置目标速度
        for mid, pos in positions.items():
            self._write2(mid, self.GOAL_SPEED, speed)
            time.sleep(0.005)
        
        # 同步写入目标位置
        self._sync_write_positions(positions)
        
        if wait:
            time.sleep(wait_time)
    
    def move_smooth(self, positions, steps=30, delay=0.03):
        """平滑移动到目标位置（插值）"""
        current = self.read_all_positions()
        
        for step in range(1, steps + 1):
            t = step / steps
            target = {}
            for mid in range(1, 7):
                if mid in positions:
                    start = current.get(mid, 2048)
                    end = positions[mid]
                    target[mid] = int(start + (end - start) * t)
                else:
                    target[mid] = current.get(mid, 2048)
            
            self._sync_write_positions(target)
            time.sleep(delay)
    
    def open_gripper(self, pos=1258):
        """张开夹爪（值越小越张开）"""
        self.move_to({6: pos}, wait=True, wait_time=0.8)
    
    def close_gripper(self, pos=1740):
        """闭合夹爪（值越大越闭合）"""
        self.move_to({6: pos}, wait=True, wait_time=0.8)
    
    def is_moving(self):
        """检查是否有电机在运动"""
        for mid in range(1, 7):
            moving = self._read1(mid, self.MOVING)
            if moving == 1:
                return True
        return False
    
    def wait_until_stopped(self, timeout=5.0):
        """等待运动停止"""
        start = time.time()
        while time.time() - start < timeout:
            if not self.is_moving():
                return True
            time.sleep(0.05)
        return False
