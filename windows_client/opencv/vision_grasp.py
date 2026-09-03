"""
夹爪摄像头 - 视觉伺服抓取脚本

工作原理:
  1. 机械臂移动到搜索位置（夹爪朝下，俯视桌面）
  2. 摄像头检测画面中的物体
  3. 根据物体在画面中的偏移，微调机械臂位置（视觉伺服）
  4. 物体到达画面中心后，下降抓取
  5. 移动到放置位置释放

不需要全局标定！靠"让物体到画面中心"来对准

用法:
  python vision_grasp.py              # 默认摄像头0，检测红色
  python vision_grasp.py 0 green      # 检测绿色
  python vision_grasp.py 0 red green  # 检测多种颜色
"""
import cv2
import numpy as np
import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "grap001"))

from detect_object import detect_color_objects, COLOR_DISPLAY
from arm_controller import SoArmController

POSITIONS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "grap001", "positions.json"
)

def load_positions():
    if os.path.exists(POSITIONS_FILE):
        with open(os.path.join(POSITIONS_FILE), 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {name: {int(k): v for k, v in pos.items()} for name, pos in data.items()}
    return {}

def load_search_poses():
    """加载搜索位置（从search_poses.json）"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_poses.json")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {name: {int(k): v for k, v in pos.items()} for name, pos in data.items()}
    return {}

def main():
    cam_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    colors = sys.argv[2:] if len(sys.argv) > 2 else ['red']
    
    print("=" * 60)
    print("SoArm101 夹爪摄像头视觉伺服抓取")
    print("=" * 60)
    
    # 加载位置
    positions = load_positions()
    search_poses = load_search_poses()
    
    if 'home' not in positions:
        print("\n缺少 home 位置，请先用 record_positions.py 记录")
        return
    
    if not search_poses:
        print("\n未找到搜索位置配置")
        print("请先运行: python setup_search.py 记录搜索位置")
        return
    
    print(f"\n摄像头: {cam_id}（夹爪摄像头）")
    print(f"检测颜色: {', '.join(colors)}")
    print(f"搜索位置: {', '.join(search_poses.keys())}")
    print(f"放置位置: {', '.join(positions.keys())}")
    
    # 连接机械臂
    print("\n连接机械臂...")
    arm = SoArmController(port="COM3")
    arm.connect()
    time.sleep(0.3)
    
    arm.enable_torque()
    time.sleep(0.3)
    
    # 移动到home
    print("移动到home位置...")
    arm.move_smooth(positions['home'], steps=20, delay=0.03)
    time.sleep(0.5)
    
    # 打开摄像头
    cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("无法打开摄像头")
        arm.disable_torque()
        arm.disconnect()
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("\n" + "=" * 60)
    print("视觉伺服抓取已启动！")
    print("=" * 60)
    print()
    print("工作流程:")
    print("  1. 机械臂依次移动到搜索位置")
    print("  2. 在每个位置用摄像头检测物体")
    print("  3. 检测到物体后微调位置，让物体到画面中心")
    print("  4. 对准后下降抓取")
    print("  5. 移动到放置位置释放")
    print()
    print("按键:")
    print("  g     - 开始搜索并抓取")
    print("  h     - 回到home位置")
    print("  v     - 切换实时检测显示")
    print("  q/Esc - 退出")
    print("=" * 60)
    
    grasp_count = 0
    live_detect = True
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if live_detect:
            # 实时检测显示
            for color_name in colors:
                objects, _ = detect_color_objects(frame, color_name)
                for obj in objects:
                    cx, cy = obj['center']
                    color = COLOR_DISPLAY[color_name]
                    cv2.circle(frame, (cx, cy), 8, color, 2)
                    cv2.putText(frame, f"{color_name} ({cx},{cy})",
                                (cx-40, cy-15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # 画中心十字
            h, w = frame.shape[:2]
            cv2.line(frame, (w//2-15, h//2), (w//2+15, h//2), (0, 255, 0), 1)
            cv2.line(frame, (w//2, h//2-15), (w//2, h//2+15), (0, 255, 0), 1)
            cv2.circle(frame, (w//2, h//2), 3, (0, 255, 0), -1)
        
        info = f"Grasped: {grasp_count} | Live: {'ON' if live_detect else 'OFF'}"
        cv2.putText(frame, info, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow("Vision Servo", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('g'):
            # 执行搜索抓取
            print("\n开始搜索物体...")
            success = search_and_grasp(arm, cap, colors, positions, search_poses)
            if success:
                grasp_count += 1
                print(f"✓ 抓取成功! (第{grasp_count}次)")
            else:
                print("✗ 未找到物体或抓取失败")
        elif key == ord('h'):
            print("\n回到home...")
            arm.move_smooth(positions['home'], steps=20, delay=0.03)
        elif key == ord('v'):
            live_detect = not live_detect
    
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n回到home...")
    arm.move_smooth(positions['home'], steps=20, delay=0.03)
    arm.disable_torque()
    arm.disconnect()
    print(f"\n完成! 共抓取 {grasp_count} 次")

def search_and_grasp(arm, cap, colors, positions, search_poses):
    """搜索物体并抓取"""
    
    for pose_name in sorted(search_poses.keys()):
        search_pose = search_poses[pose_name]
        
        print(f"\n  搜索位置: {pose_name}")
        print(f"    移动到搜索位置...")
        arm.move_smooth(search_pose, steps=20, delay=0.03)
        time.sleep(0.5)
        
        # 在此位置检测物体
        ret, frame = cap.read()
        if not ret:
            continue
        
        all_objects = []
        for color_name in colors:
            objects, _ = detect_color_objects(frame, color_name)
            for obj in objects:
                all_objects.append((obj, color_name))
        
        if not all_objects:
            print(f"    未检测到物体，继续搜索...")
            continue
        
        # 找最大的物体
        best_obj, best_color = max(all_objects, key=lambda x: x[0]['area'])
        cx, cy = best_obj['center']
        print(f"    发现 {best_color} 物体! 位置=({cx},{cy}) 面积={int(best_obj['area'])}")
        
        # 视觉伺服：微调位置让物体到画面中心
        print(f"    视觉伺服对准中...")
        aligned = visual_servo(arm, cap, colors, search_pose)
        
        if not aligned:
            print(f"    对准失败，跳过")
            continue
        
        # 对准了，执行抓取
        print(f"    对准成功! 开始抓取...")
        return execute_grasp_at_center(arm, search_pose, positions)
    
    return False

def visual_servo(arm, cap, colors, start_pose, max_iters=15):
    """
    视觉伺服：根据物体在画面中的偏移微调机械臂
    物体偏左 → 机械臂往左转（shoulder_pan +）
    物体偏上 → 机械臂往前伸（elbow_flex 调整）
    """
    current_pose = start_pose.copy()
    
    h, w = 480, 640  # 默认分辨率
    center_x, center_y = w // 2, h // 2
    
    # 微调步长（每次迭代调整多少）
    PAN_STEP = 15       # shoulder_pan 每次调整量
    LIFT_STEP = 10      # shoulder_lift
    ELBOW_STEP = 15     # elbow_flex
    
    # 死区：物体离中心多近就算对准了
    DEAD_ZONE = 30
    
    for iteration in range(max_iters):
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue
        
        # 更新实际分辨率
        h, w = frame.shape[:2]
        center_x, center_y = w // 2, h // 2
        
        # 检测物体
        all_objects = []
        for color_name in colors:
            objects, _ = detect_color_objects(frame, color_name)
            for obj in objects:
                all_objects.append((obj, color_name))
        
        if not all_objects:
            print(f"      迭代{iteration+1}: 物体丢失")
            return False
        
        # 找最大的物体
        best_obj, best_color = max(all_objects, key=lambda x: x[0]['area'])
        cx, cy = best_obj['center']
        
        # 计算偏移
        dx = cx - center_x  # 正=偏右，负=偏左
        dy = cy - center_y  # 正=偏下，负=偏上
        
        print(f"      迭代{iteration+1}: ({cx},{cy}) 偏移 dx={dx:+4d} dy={dy:+4d}")
        
        # 检查是否已对准
        if abs(dx) < DEAD_ZONE and abs(dy) < DEAD_ZONE:
            print(f"      ✓ 已对准中心!")
            return True
        
        # 根据偏移调整关节角度
        adjusted = False
        
        # X方向：物体偏左→pan增大，偏右→pan减小
        if abs(dx) > DEAD_ZONE:
            # 注意：这里的方向需要根据实际安装调整
            # 如果机械臂往右移时物体在画面中也往右，则取反
            step = PAN_STEP if dx > 0 else -PAN_STEP
            # 死区外按比例调整
            step = int(step * min(abs(dx) / 100, 2))
            new_val = max(0, min(4095, current_pose[1] + step))
            if new_val != current_pose[1]:
                current_pose[1] = new_val
                adjusted = True
        
        # Y方向：物体偏上（dy<0）→机械臂往前伸，偏下→往回缩
        if abs(dy) > DEAD_ZONE:
            # 偏上→elbow增大（往前伸），偏下→elbow减小
            step = ELBOW_STEP if dy < 0 else -ELBOW_STEP
            step = int(step * min(abs(dy) / 100, 2))
            new_val = max(0, min(4095, current_pose[3] + step))
            if new_val != current_pose[3]:
                current_pose[3] = new_val
                adjusted = True
        
        if not adjusted:
            print(f"      无需调整")
            return True
        
        # 移动到新位置
        arm._sync_write_positions(current_pose)
        time.sleep(0.3)  # 等待机械臂稳定
        
        # 显示画面
        for color_name in colors:
            objects, _ = detect_color_objects(frame, color_name)
            for obj in objects:
                ox, oy = obj['center']
                color = COLOR_DISPLAY[color_name]
                cv2.circle(frame, (ox, oy), 8, color, 2)
        cv2.line(frame, (center_x-15, center_y), (center_x+15, center_y), (0, 255, 0), 1)
        cv2.line(frame, (center_x, center_y-15), (center_x, center_y+15), (0, 255, 0), 1)
        cv2.imshow("Vision Servo", frame)
        cv2.waitKey(1)
    
    print(f"      达到最大迭代次数")
    return False

def execute_grasp_at_center(arm, current_pose, positions):
    """在当前对准位置执行抓取"""
    try:
        # 1. 张开夹爪
        print("    [1/5] 张开夹爪...")
        grasp_pose = current_pose.copy()
        grasp_pose[6] = 1258
        arm._sync_write_positions(grasp_pose)
        time.sleep(0.5)
        
        # 2. 下降（shoulder_lift减小 = 往下）
        print("    [2/5] 下降...")
        down_pose = grasp_pose.copy()
        down_pose[2] = max(0, grasp_pose[2] - 150)
        arm.move_smooth(down_pose, steps=10, delay=0.04)
        time.sleep(0.3)
        
        # 3. 闭合夹爪
        print("    [3/5] 闭合夹爪...")
        down_pose[6] = 1740
        arm._sync_write_positions(down_pose)
        time.sleep(0.5)
        
        # 4. 抬起
        print("    [4/5] 抬起...")
        up_pose = down_pose.copy()
        up_pose[2] = grasp_pose[2]
        arm.move_smooth(up_pose, steps=10, delay=0.04)
        time.sleep(0.3)
        
        # 5. 移动到放置位置
        if 'place' in positions:
            print("    [5/5] 移动到放置位置并释放...")
            arm.move_smooth(positions['place'], steps=20, delay=0.03)
            time.sleep(0.3)
            
            # 释放
            release_pose = positions['place'].copy()
            release_pose[6] = 1258
            arm._sync_write_positions(release_pose)
            time.sleep(0.5)
            
            # 回home
            if 'home' in positions:
                arm.move_smooth(positions['home'], steps=20, delay=0.03)
                time.sleep(0.3)
        
        return True
        
    except Exception as e:
        print(f"    抓取出错: {e}")
        return False

if __name__ == "__main__":
    main()
