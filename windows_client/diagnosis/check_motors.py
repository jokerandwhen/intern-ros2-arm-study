from lerobot.motors.feetech.feetech import FeetechMotorsBus
from lerobot.motors.feetech import MODEL_NUMBER

# 扫描COM4上所有电机
bus = FeetechMotorsBus(
    port="COM4",
    motors={}  # 空配置，扫描所有ID
)

print("正在扫描 COM4 上的所有电机...")
print("=" * 50)

try:
    bus.connect()

    # 扫描ID范围 1-10
    found_motors = {}
    for motor_id in range(1, 11):
        try:
            model_number = bus.read(motor_id, 0, 2)
            if model_number:
                model_name = MODEL_NUMBER.get(model_number, f"Unknown({model_number})")
                found_motors[motor_id] = model_name
                print(f"✓ 找到电机 ID={motor_id}: {model_name} (型号: {model_number})")
        except Exception as e:
            pass  # 该ID无响应

    print("\n" + "=" * 50)
    print(f"共找到 {len(found_motors)} 个电机")
    print(f"缺失的电机ID: {set(range(1, 7)) - set(found_motors.keys())}")

except Exception as e:
    print(f"错误: {e}")
finally:
    bus.disconnect()