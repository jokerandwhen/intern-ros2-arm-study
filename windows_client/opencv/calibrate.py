"""
像素坐标到机械臂关节角度的标定脚本

通过点击画面中的已知机械臂位置，建立像素坐标→关节角度的映射关系

标定流程:
  1. 将机械臂移动到画面中不同位置（至少3个点）
  2. 每个位置记录: 像素坐标(x,y) + 机械臂关节角度(shoulder_pan, shoulder_lift, elbow_flex)
  3. 程序自动拟合映射关系

用法:
  python calibrate.py
"""
import cv2
import numpy as np
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "grap001"))

CALIB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration.json")

def main():
    print("=" * 60)
    print("像素坐标 → 机械臂角度 标定工具")
    print("=" * 60)
    print()
    print("标定说明:")
    print("  1. 摄像头画面会显示机械臂工作区域")
    print("  2. 用 keyboard_control.py 把机械臂移动到画面中某个位置")
    print("  3. 点击画面中夹爪的位置，记录像素坐标")
    print("  4. 输入当时的关节角度（或自动读取）")
    print("  5. 至少标定3个点（建议5个点覆盖工作区域）")
    print("  6. 程序自动拟合像素→角度的映射")
    print()
    
    # 尝试连接机械臂自动读取角度
    arm = None
    try:
        from arm_controller import SoArmController
        arm = SoArmController(port="COM3")
        arm.connect()
        print("✓ 机械臂已连接，可自动读取角度")
    except Exception as e:
        print(f"⚠ 机械臂未连接 ({e})，需手动输入角度")
    
    # 打开摄像头
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("无法打开摄像头")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    calibration_points = []
    click_pos = None
    
    def on_mouse(event, x, y, flags, param):
        nonlocal click_pos
        if event == cv2.EVENT_LBUTTONDOWN:
            click_pos = (x, y)
    
    cv2.namedWindow("Calibration", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("Calibration", on_mouse)
    
    print("\n操作说明:")
    print("  鼠标点击 - 标定当前夹爪位置")
    print("  a       - 自动读取机械臂角度（需连接机械臂）")
    print("  d       - 删除上一个标定点")
    print("  s       - 保存标定结果")
    print("  q/Esc   - 退出")
    print()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 画十字准线
        h, w = frame.shape[:2]
        cv2.line(frame, (w//2, 0), (w//2, h), (0, 255, 0), 1)
        cv2.line(frame, (0, h//2), (w, h//2), (0, 255, 0), 1)
        
        # 显示已标定的点
        for i, pt in enumerate(calibration_points):
            px, py = pt['pixel']
            cv2.circle(frame, (px, py), 8, (0, 0, 255), 2)
            cv2.putText(frame, f"P{i+1}", (px+10, py-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        # 显示点击位置
        if click_pos:
            cv2.circle(frame, click_pos, 10, (255, 0, 0), 2)
            cv2.putText(frame, f"Click: {click_pos}", (10, 460),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
        
        info = f"Points: {len(calibration_points)}"
        cv2.putText(frame, info, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow("Calibration", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('a') and click_pos:
            # 自动读取机械臂角度
            if arm:
                pos = arm.read_all_positions()
                point = {
                    'pixel': click_pos,
                    'joints': {str(k): v for k, v in pos.items()},
                }
                calibration_points.append(point)
                print(f"\n标定点 {len(calibration_points)}: pixel={click_pos} joints={pos}")
                click_pos = None
            else:
                print("\n机械臂未连接，请手动输入")
        elif key == ord('d'):
            if calibration_points:
                removed = calibration_points.pop()
                print(f"\n删除点: {removed['pixel']}")
        elif key == ord('s'):
            if len(calibration_points) >= 3:
                # 保存标定数据
                with open(CALIB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(calibration_points, f, indent=2, ensure_ascii=False)
                print(f"\n✓ 标定数据已保存到 {CALIB_FILE} ({len(calibration_points)}个点)")
            else:
                print(f"\n⚠ 至少需要3个点，当前只有{len(calibration_points)}个")
    
    cap.release()
    cv2.destroyAllWindows()
    
    if arm:
        arm.disconnect()
    
    # 如果有足够的点，拟合映射关系
    if len(calibration_points) >= 3:
        print("\n拟合映射关系...")
        fit_mapping(calibration_points)

def fit_mapping(points):
    """拟合像素坐标到关节角度的映射关系"""
    pixels = np.array([[p['pixel'][0], p['pixel'][1]] for p in points], dtype=np.float32)
    
    mapping = {}
    for joint_id in ['1', '2', '3']:
        angles = np.array([p['joints'][joint_id] for p in points], dtype=np.float32)
        
        # 线性拟合: angle = a*px + b*py + c
        A = np.column_stack([pixels, np.ones(len(pixels))])
        result, _, _, _ = np.linalg.lstsq(A, angles, rcond=None)
        a, b, c = result
        
        mapping[joint_id] = {'a': float(a), 'b': float(b), 'c': float(c)}
        
        # 计算拟合误差
        predicted = A @ result
        errors = np.abs(predicted - angles)
        print(f"  关节{joint_id}: angle = {a:.2f}*x + {b:.2f}*y + {c:.1f}  最大误差={errors.max():.1f}")
    
    # 保存映射关系
    with open(CALIB_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    result_data = {
        'points': data,
        'mapping': mapping,
    }
    
    with open(CALIB_FILE, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ 映射关系已保存到 {CALIB_FILE}")

def pixel_to_angle(px, py):
    """像素坐标转关节角度（使用标定结果）"""
    if not os.path.exists(CALIB_FILE):
        print("标定文件不存在，请先运行 calibrate.py")
        return None
    
    with open(CALIB_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'mapping' not in data:
        print("标定数据不完整")
        return None
    
    mapping = data['mapping']
    result = {}
    for joint_id, coeff in mapping.items():
        angle = coeff['a'] * px + coeff['b'] * py + coeff['c']
        result[int(joint_id)] = int(max(0, min(4095, angle)))
    
    return result

if __name__ == "__main__":
    main()
