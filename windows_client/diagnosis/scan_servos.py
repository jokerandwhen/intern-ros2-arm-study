"""使用底层协议扫描舵机"""
import serial
import time

def scan_servos():
    print("[INFO] 开始扫描舵机...")
    print("[INFO] 请确保：")
    print("  1. 控制板已通过USB连接到COM3")
    print("  2. 舵机电源已开启（舵机红灯亮）")
    print("  3. 舵机线已连接到控制板\n")

    try:
        # 尝试不同波特率
        baudrates = [1000000, 115200, 57600, 9600]

        for baudrate in baudrates:
            print(f"\n尝试波特率: {baudrate}")
            try:
                ser = serial.Serial(
                    port='COM3',
                    baudrate=baudrate,
                    timeout=1,
                    write_timeout=1
                )

                # 给控制板发送ping指令，检测舵机
                for motor_id in range(1, 7):
                    try:
                        # 构造简单的ping指令（Feetech协议）
                        ping_cmd = bytes([0xFF, 0xFF, motor_id, 0x02, 0x01])
                        ser.write(ping_cmd)
                        time.sleep(0.01)

                        # 读取响应
                        if ser.in_waiting > 0:
                            response = ser.read(ser.in_waiting)
                            print(f"  [OK] 检测到舵机 ID={motor_id}, 响应: {response.hex()}")
                    except Exception as e:
                        pass

                ser.close()

            except Exception as e:
                print(f"  [WARN] 波特率 {baudrate} 打开失败: {e}")

        print("\n" + "="*50)
        print("如果上面没有检测到任何舵机，请检查：")
        print("1. 舵机的3针信号线是否已插入控制板")
        print("2. 控制板型号是否为Feetech/飞特")
        print("3. 舵机电源是否充足（红灯常亮）")
        print("="*50)

    except Exception as e:
        print(f"[ERROR] 扫描失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    scan_servos()