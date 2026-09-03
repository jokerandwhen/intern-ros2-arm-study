"""
物体检测脚本
基于颜色+轮廓检测识别物体位置和大小

支持检测的颜色:
  red    - 红色
  green  - 绿色
  blue   - 蓝色
  yellow - 黄色
  orange - 橙色

用法:
  python detect_object.py              # 默认摄像头0，检测所有颜色
  python detect_object.py 0 red        # 指定摄像头和颜色
  python detect_object.py 0 red green  # 检测多种颜色
"""
import cv2
import numpy as np
import sys

# 颜色HSV范围 (H: 0-179, S: 0-255, V: 0-255)
COLOR_RANGES = {
    'red': [
        ((0, 100, 100), (10, 255, 255)),      # 低色相红色
        ((170, 100, 100), (179, 255, 255)),   # 高色相红色
    ],
    'green': [
        ((35, 50, 50), (85, 255, 255)),
    ],
    'blue': [
        ((85, 50, 50), (130, 255, 255)),
    ],
    'yellow': [
        ((20, 100, 100), (35, 255, 255)),
    ],
    'orange': [
        ((10, 100, 100), (25, 255, 255)),
    ],
}

COLOR_DISPLAY = {
    'red':    (0, 0, 255),
    'green':  (0, 255, 0),
    'blue':   (255, 0, 0),
    'yellow': (0, 255, 255),
    'orange': (0, 165, 255),
}

def detect_color_objects(frame, color_name, min_area=300):
    """检测指定颜色的物体"""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lower, upper in COLOR_RANGES[color_name]:
        lower_np = np.array(lower)
        upper_np = np.array(upper)
        mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lower_np, upper_np))
    
    # 形态学操作去噪
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # 找轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    objects = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        
        # 最小外接矩形
        rect = cv2.minAreaRect(cnt)
        cx, cy = int(rect[0][0]), int(rect[0][1])
        w, h = rect[1]
        angle = rect[2]
        
        # 外接圆
        (circle_x, circle_y), radius = cv2.minEnclosingCircle(cnt)
        
        objects.append({
            'center': (cx, cy),
            'area': area,
            'rect': rect,
            'radius': radius,
            'circle_center': (int(circle_x), int(circle_y)),
            'bbox': cv2.boundingRect(cnt),
        })
    
    return objects, mask

def draw_detections(frame, objects, color_name):
    """在画面上绘制检测结果"""
    color = COLOR_DISPLAY[color_name]
    
    for obj in objects:
        cx, cy = obj['center']
        
        # 画外接矩形
        box = cv2.boxPoints(obj['rect'])
        box = np.int0(box)
        cv2.drawContours(frame, [box], 0, color, 2)
        
        # 画中心点
        cv2.circle(frame, (cx, cy), 5, color, -1)
        
        # 画外接圆
        cv2.circle(frame, obj['circle_center'], int(obj['radius']), color, 1)
        
        # 标注信息
        label = f"{color_name} ({cx},{cy}) A={int(obj['area'])}"
        cv2.putText(frame, label, (cx - 60, cy - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    return frame

def main():
    cam_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    
    if len(sys.argv) > 2:
        colors_to_detect = sys.argv[2:]
    else:
        colors_to_detect = list(COLOR_RANGES.keys())
    
    # 验证颜色名称
    for c in colors_to_detect:
        if c not in COLOR_RANGES:
            print(f"未知颜色: {c}")
            print(f"可用颜色: {', '.join(COLOR_RANGES.keys())}")
            return
    
    cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"无法打开摄像头 {cam_id}")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print(f"摄像头 {cam_id} 已打开")
    print(f"检测颜色: {', '.join(colors_to_detect)}")
    print()
    print("操作说明:")
    print("  q/Esc  - 退出")
    print("  m      - 显示/隐藏mask画面")
    print("  s      - 截图")
    print()
    
    show_mask = False
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        all_objects = []
        
        for color_name in colors_to_detect:
            objects, mask = detect_color_objects(frame, color_name)
            all_objects.extend([(obj, color_name) for obj in objects])
            frame = draw_detections(frame, objects, color_name)
        
        # 显示检测到的物体数量
        info = f"Detected: {len(all_objects)} objects"
        cv2.putText(frame, info, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # 如果检测到物体，打印最近的一个
        if all_objects:
            # 找面积最大的物体
            best = max(all_objects, key=lambda x: x[0]['area'])
            obj, cname = best
            cx, cy = obj['center']
            print(f"\r最大物体: {cname} 位置=({cx:4d},{cy:4d}) 面积={int(obj['area']):6d}    ", end='', flush=True)
        
        cv2.imshow("Detection", frame)
        
        if show_mask:
            # 显示所有颜色的mask
            masks = []
            for color_name in colors_to_detect:
                _, mask = detect_color_objects(frame, color_name)
                masks.append(mask)
            combined = cv2.bitwise_or(masks[0], masks[1]) if len(masks) > 1 else masks[0]
            for m in masks[2:]:
                combined = cv2.bitwise_or(combined, m)
            cv2.imshow("Mask", combined)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('m'):
            show_mask = not show_mask
            if not show_mask:
                cv2.destroyWindow("Mask")
        elif key == ord('s'):
            cv2.imwrite("detection_snapshot.jpg", frame)
            print("\n截图已保存: detection_snapshot.jpg")
    
    cap.release()
    cv2.destroyAllWindows()
    print("\n已关闭")

if __name__ == "__main__":
    main()
