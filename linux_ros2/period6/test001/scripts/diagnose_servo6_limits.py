#!/usr/bin/env python3
"""诊断舵机6的位置限制寄存器"""

import scservo_sdk as scs

# 初始化
PORT = '/dev/ttyACM0'
BAUDRATE = 1000000
SERVO_ID = 6  # joint6对应的舵机ID

# STS3215寄存器地址（参考feetech/tables.py）
ADDR_MIN_POSITION_LIMIT = 25  # Min_Position_Limit（2字节）
ADDR_MAX_POSITION_LIMIT = 27  # Max_Position_Limit（2字节）
ADDR_PRESENT_POSITION = 56    # Present_Position（2字节）

# 初始化SDK
port_handler = scs.PortHandler(PORT)
packet_handler = scs.protocol_packet_handler()  # 小写函数名

try:
    if not port_handler.openPort():
        print(f"无法打开端口 {PORT}")
        exit(1)
    
    if not port_handler.setBaudRate(BAUDRATE):
        print(f"无法设置波特率 {BAUDRATE}")
        exit(1)
    
    print("="*60)
    print("舵机6位置限制诊断")
    print("="*60)
    
    # 读取Min_Position_Limit（地址25-26）
    min_limit, result, error = packet_handler.read2ByteTxRx(
        port_handler, SERVO_ID, ADDR_MIN_POSITION_LIMIT
    )
    
    if result == 0 and error == 0:
        print(f"✓ Min_Position_Limit: {min_limit} （地址25）")
    else:
        print(f"✗ 读取Min_Position_Limit失败: result={result}, error={error}")
    
    # 读取Max_Position_Limit（地址27-28）
    max_limit, result, error = packet_handler.read2ByteTxRx(
        port_handler, SERVO_ID, ADDR_MAX_POSITION_LIMIT
    )
    
    if result == 0 and error == 0:
        print(f"✓ Max_Position_Limit: {max_limit} （地址27）")
        
        if max_limit == 4095:
            print("  ⚠️  限制为4095，这可能是问题所在！")
            print("  舵机无法接受超过4095的脉冲值")
        elif max_limit >= 5474:
            print("  ✓ 限制足够大，应该能接受脉冲5474")
        else:
            print(f"  ⚠️  限制为{max_limit}，可能不够大")
    else:
        print(f"✗ 读取Max_Position_Limit失败: result={result}, error={error}")
    
    # 读取当前位置
    current_pos, result, error = packet_handler.read2ByteTxRx(
        port_handler, SERVO_ID, ADDR_PRESENT_POSITION
    )
    
    if result == 0 and error == 0:
        print(f"✓ Present_Position: {current_pos} （地址56）")
    else:
        print(f"✗ 读取Present_Position失败: result={result}, error={error}")
    
    print("="*60)
    
    # 测试：尝试写入脉冲4500（超过4095）
    print("\n测试：尝试写入脉冲4500...")
    test_pulse = 4500
    result, error = packet_handler.write2ByteTxRx(
        port_handler, SERVO_ID, 42, test_pulse  # 地址42是Goal_Position
    )
    
    if result == 0 and error == 0:
        print(f"✓ 写入脉冲{test_pulse}成功")
        
        # 等待并读取实际位置
        import time
        time.sleep(1)
        
        actual_pos, result, error = packet_handler.read2ByteTxRx(
            port_handler, SERVO_ID, ADDR_PRESENT_POSITION
        )
        
        if result == 0 and error == 0:
            print(f"  实际位置: {actual_pos}")
            
            if actual_pos >= 4095:
                print("  ✓ 舵机能接受超过4095的脉冲！")
            else:
                print(f"  ✗ 实际位置只有{actual_pos}，可能被限制在4095")
        else:
            print(f"  ✗ 读取实际位置失败")
    else:
        print(f"✗ 写入脉冲{test_pulse}失败: result={result}, error={error}")
    
    print("="*60)
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

finally:
    port_handler.closePort()
    print("连接已关闭")