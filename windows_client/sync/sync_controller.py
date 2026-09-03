"""
SoArm101 双臂同步控制器
主臂（Leader/COM4）读取位置 → 从动臂（Follower/COM3）跟随运动

基于正确的STS3215寄存器地址，高速读取主臂位置实时同步到从动臂
"""
import serial
import time

class SyncController:
    """双臂同步控制器"""
    
    # STS3215 寄存器地址
    TORQUE_ENABLE = 40
    ACCELERATION = 41
    GOAL_POSITION = 42
    GOAL_SPEED = 46
    TORQUE_LIMIT = 48
    PRESENT_POSITION = 56
    PRESENT_VOLTAGE = 62
    PRESENT_TEMP = 63
    STATUS = 65
    
    MOTOR_NAMES = {1: "shoulder_pan", 2: "shoulder_lift", 3: "elbow_flex",
                   4: "wrist_flex", 5: "wrist_roll", 6: "gripper"}
    
    def __init__(self, leader_port="COM4", follower_port="COM3", baud=1000000):
        self.leader_port = leader_port
        self.follower_port = follower_port
        self.baud = baud
        self.leader_ser = None
        self.follower_ser = None
        # 偏移量：主臂和从动臂的中性位置差异
        self.offsets = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        # 比例：主臂和从动臂的运动方向可能相反
        self.scales = {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1}
    
    def connect(self):
        """连接两个串口"""
        self.leader_ser = serial.Serial(self.leader_port, baudrate=self.baud, timeout=0.1)
        self.follower_ser = serial.Serial(self.follower_port, baudrate=self.baud, timeout=0.1)
        time.sleep(0.3)
        
        # 禁用扭矩、设置加速度
        for ser, name in [(self.leader_ser, "主臂"), (self.follower_ser, "从动臂")]:
            for mid in range(1, 7):
                self._write1(ser, mid, self.TORQUE_ENABLE, 0)
                time.sleep(0.005)
                self._write1(ser, mid, self.ACCELERATION, 254)
                time.sleep(0.005)
        
        print(f"✓ 主臂已连接 {self.leader_port}")
        print(f"✓ 从动臂已连接 {self.follower_port}")
    
    def disconnect(self):
        """断开连接"""
        for ser, name in [(self.leader_ser, "主臂"), (self.follower_ser, "从动臂")]:
            if ser and ser.is_open:
                try:
                    for mid in range(1, 7):
                        try:
                            self._write1(ser, mid, self.TORQUE_ENABLE, 0)
                        except:
                            pass
                        time.sleep(0.005)
                    ser.close()
                except:
                    pass
        print("✓ 双臂已断开")
    
    def _build_packet(self, mid, instr, params=b''):
        length = len(params) + 2
        pkt = bytes([0xFF, 0xFF, mid, length, instr]) + params
        cs = (~sum(pkt[2:]) & 0xFF)
        return pkt + bytes([cs])
    
    def _write1(self, ser, mid, addr, val):
        ser.reset_input_buffer()
        ser.write(self._build_packet(mid, 0x03, bytes([addr, val & 0xFF])))
        time.sleep(0.005)
    
    def _write2(self, ser, mid, addr, val):
        ser.reset_input_buffer()
        ser.write(self._build_packet(mid, 0x03,
            bytes([addr, val & 0xFF, (val >> 8) & 0xFF])))
        time.sleep(0.005)
    
    def _read2(self, ser, mid, addr):
        """读2字节寄存器"""
        for _ in range(3):
            ser.reset_input_buffer()
            ser.write(self._build_packet(mid, 0x02, bytes([addr, 2])))
            time.sleep(0.015)
            r = ser.read(64)
            if len(r) >= 7:
                return r[5] | (r[6] << 8)
            time.sleep(0.01)
        return None
    
    def _read_position_fast(self, ser, mid):
        """高速读取单个电机位置"""
        for _ in range(2):
            ser.reset_input_buffer()
            ser.write(self._build_packet(mid, 0x02, bytes([self.PRESENT_POSITION, 2])))
            time.sleep(0.005)
            r = ser.read(8)
            if len(r) >= 8 and r[0] == 0xFF and r[1] == 0xFF:
                return r[5] | (r[6] << 8)
            if ser.in_waiting > 0:
                ser.read(ser.in_waiting)
        return None
    
    def _sync_write_positions(self, ser, positions_dict):
        """同步写多电机目标位置"""
        params = bytes([self.GOAL_POSITION, 2])
        for mid, pos in positions_dict.items():
            params += bytes([mid, pos & 0xFF, (pos >> 8) & 0xFF])
        ser.reset_input_buffer()
        ser.write(self._build_packet(0xFE, 0x83, params))
        time.sleep(0.003)
    
    def read_all_positions(self, ser, fast=True):
        """读取所有电机位置"""
        positions = {}
        for mid in range(1, 7):
            if fast:
                pos = self._read_position_fast(ser, mid)
            else:
                pos = self._read2(ser, mid, self.PRESENT_POSITION)
            positions[mid] = pos if pos is not None else 2048
        return positions
    
    def read_status(self, ser, label=""):
        """读取所有电机状态"""
        result = {}
        for mid in range(1, 7):
            status = None
            for _ in range(2):
                ser.reset_input_buffer()
                ser.write(self._build_packet(mid, 0x02, bytes([self.STATUS, 1])))
                time.sleep(0.01)
                r = ser.read(20)
                if len(r) >= 6:
                    status = r[5]
                    break
            result[mid] = status or 0
        return result
    
    def enable_follower_torque(self):
        """使能从动臂扭矩"""
        for mid in range(1, 7):
            self._write2(self.follower_ser, mid, self.TORQUE_LIMIT, 1023)
            time.sleep(0.005)
            self._write1(self.follower_ser, mid, self.TORQUE_ENABLE, 1)
            time.sleep(0.005)
        print("✓ 从动臂扭矩已使能")
    
    def disable_all_torque(self):
        """禁用所有扭矩"""
        for ser in [self.leader_ser, self.follower_ser]:
            for mid in range(1, 7):
                try:
                    self._write1(ser, mid, self.TORQUE_ENABLE, 0)
                except:
                    pass
                time.sleep(0.005)
        print("✓ 双臂扭矩已禁用")
    
    def calibrate_offsets(self):
        """校准偏移量：读取两臂当前位置，计算偏移"""
        leader_pos = self.read_all_positions(self.leader_ser, fast=False)
        follower_pos = self.read_all_positions(self.follower_ser, fast=False)
        
        print("\n校准偏移量：")
        print(f"  {'关节':<15} {'主臂':>6} {'从动臂':>6} {'偏移':>6}")
        for mid in range(1, 7):
            self.offsets[mid] = follower_pos[mid] - leader_pos[mid]
            print(f"  {self.MOTOR_NAMES[mid]:<15} {leader_pos[mid]:>6} {follower_pos[mid]:>6} {self.offsets[mid]:>6}")
        
        return leader_pos, follower_pos
    
    def leader_to_follower(self, leader_pos):
        """将主臂位置转换为从动臂目标位置"""
        target = {}
        for mid in range(1, 7):
            val = leader_pos[mid] + self.offsets[mid]
            val = max(0, min(4095, val))
            target[mid] = val
        return target
    
    def sync_step(self):
        """执行一次同步：读取主臂位置 → 写入从动臂"""
        leader_pos = self.read_all_positions(self.leader_ser, fast=True)
        target = self.leader_to_follower(leader_pos)
        self._sync_write_positions(self.follower_ser, target)
        return leader_pos, target
