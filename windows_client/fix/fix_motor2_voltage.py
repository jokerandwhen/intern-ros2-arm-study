"""
底层修复电机2电压上限
使用 SCServo SDK 直接写入寄存器
"""

import time

def fix_motor2_voltage():
    """使用底层SDK修复电机2电压上限"""
    print("="*70)
    print("底层修复电机2电压上限")
    print("="*70)
    
    print("\n说明：")
    print("  这个脚本使用底层 SCServo SDK 直接写入寄存器")
    print("  专门修复电机2（shoulder_lift）的电压上限问题")
    
    input("\n按 Enter 继续...")
    
    try:
        # 导入底层SDK
        from scservo_sdk import PortHandler, PacketHandler
        
        print("\n[步骤1] 打开端口...")
        # 尝试打开 COM3
        port_name = "COM3"
        port = PortHandler(port_name)
        
        if not port.openPort():
            print(f"  ✗ 无法打开端口 {port_name}")
            print("  请检查：")
            print("    1. USB 线是否已插入")
            print("    2. 设备管理器中查看正确的端口")
            return
        
        print(f"  ✓ 成功打开端口 {port_name}")
        
        # 设置波特率
        if not port.setBaudRate(1000000):
            print("  ✗ 无法设置波特率")
            port.closePort()
            return
        
        print("  ✓ 波特率设置为 1000000")
        
        # 创建 PacketHandler
        ph = PacketHandler(0)  # 0 表示 SMS/STS 协议
        
        print("\n[步骤2] 读取电机2当前电压上限...")
        motor_id = 2
        
        # 读取地址14（Max_Voltage_Limit），长度1字节
        current_voltage, comm_result, error = ph.read1ByteTxRx(port, motor_id, 14)
        
        if comm_result != 0:
            print(f"  ✗ 读取失败: {ph.getTxRxResult(comm_result)}")
            port.closePort()
            return
        
        print(f"  当前电压上限: {current_voltage / 10.0:.1f}V")
        
        if current_voltage >= 120:
            print("  ✓ 电压上限已经足够（≥12V）")
            port.closePort()
            return
        
        print("\n[步骤3] 解锁 EEPROM...")
        # 地址55（Lock）写入 0 解锁
        result, error = ph.write1ByteTxRx(port, motor_id, 55, 0)
        
        if result != 0:
            print(f"  ✗ 解锁失败: {ph.getTxRxResult(result)}")
            port.closePort()
            return
        
        print("  ✓ EEPROM 已解锁")
        
        print("\n[步骤4] 修改电压上限为 16.0V...")
        # 地址14（Max_Voltage_Limit）写入 160（代表16.0V）
        result, error = ph.write1ByteTxRx(port, motor_id, 14, 160)
        
        if result != 0:
            print(f"  ✗ 写入失败: {ph.getTxRxResult(result)}")
            port.closePort()
            return
        
        print("  ✓ 成功写入 16.0V")
        
        print("\n[步骤5] 锁定 EEPROM...")
        # 地址55（Lock）写入 1 锁定
        result, error = ph.write1ByteTxRx(port, motor_id, 55, 1)
        
        if result != 0:
            print(f"  ✗ 锁定失败: {ph.getTxRxResult(result)}")
            port.closePort()
            return
        
        print("  ✓ EEPROM 已锁定")
        
        print("\n[步骤6] 验证修改结果...")
        # 重新读取电压上限
        new_voltage, comm_result, error = ph.read1ByteTxRx(port, motor_id, 14)
        
        if comm_result != 0:
            print(f"  ✗ 验证失败: {ph.getTxRxResult(comm_result)}")
        else:
            print(f"  新电压上限: {new_voltage / 10.0:.1f}V")
            
            if new_voltage >= 120:
                print("  ✓ 修改成功！")
            else:
                print("  ⚠️ 修改可能失败，请重试")
        
        print("\n[步骤7] 清除故障锁存...")
        # 地址48（Status_Error）写入 0 清除故障
        result, error = ph.write1ByteTxRx(port, motor_id, 48, 0)
        
        if result != 0:
            print(f"  ⚠️ 清除失败: {ph.getTxRxResult(result)}")
        else:
            print("  ✓ 故障锁存已清除")
        
        # 关闭端口
        port.closePort()
        
        print("\n" + "="*70)
        print("修复完成！")
        print("="*70)
        
        print("\n下一步：")
        print("  1. 断开 USB 连接")
        print("  2. 连接 12V 电源适配器")
        print("  3. 打开机械臂电源开关")
        print("  4. 观察 LED 是否还闪烁")
        print("  5. 运行 python full_diagnosis.py 测试")
        
    except Exception as e:
        print(f"\n❌ 操作失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_motor2_voltage()