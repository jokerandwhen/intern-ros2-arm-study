"""
摄像头测试脚本
打开摄像头，实时显示画面，点击画面可以获取像素坐标
用于确定摄像头是否正常工作，以及标定机械臂的工作区域

用法:
  python camera_test.py              # 默认摄像头0
  python camera_test.py 1            # 指定摄像头编号
"""
import cv2
import numpy as np
import sys

def main():
    cam_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
    
    if not cap.isOpened():
        print(f"无法打开摄像头 {cam_id}")
        print("可用摄像头: 0, 1, 2...")
        return
    
    # 设置分辨率
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"摄像头 {cam_id} 已打开")
    print(f"分辨率: {actual_w}x{actual_h}")
    print()
    print("操作说明:")
    print("  鼠标点击  - 显示点击位置的像素坐标和HSV颜色值")
    print("  s        - 截图保存到当前目录")
    print("  r        - 显示/隐藏十字准线")
    print("  q/Esc    - 退出")
    print()
    
    click_pos = None
    show_cross = True
    
    def on_mouse(event, x, y, flags, param):
        nonlocal click_pos
        if event == cv2.EVENT_LBUTTONDOWN:
            click_pos = (x, y)
    
    cv2.namedWindow("Camera", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("Camera", on_mouse)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取画面")
            break
        
        # 翻转（如果需要镜像）
        # frame = cv2.flip(frame, 1)
        
        # 显示十字准线
        if show_cross:
            h, w = frame.shape[:2]
            cv2.line(frame, (w//2, 0), (w//2, h), (0, 255, 0), 1)
            cv2.line(frame, (0, h//2), (w, h//2), (0, 255, 0), 1)
            cv2.circle(frame, (w//2, h//2), 5, (0, 255, 0), -1)
            cv2.putText(frame, f"Center: ({w//2}, {h//2})", (10, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # 显示点击位置信息
        if click_pos:
            x, y = click_pos
            # 画标记
            cv2.circle(frame, (x, y), 8, (0, 0, 255), 2)
            cv2.line(frame, (x-15, y), (x+15, y), (0, 0, 255), 1)
            cv2.line(frame, (x, y-15), (x, y+15), (0, 0, 255), 1)
            
            # 读取HSV颜色
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            b, g, r = frame[y, x]
            h_val, s_val, v_val = hsv[y, x]
            
            info = f"({x},{y}) BGR=({b},{g},{r}) HSV=({h_val},{s_val},{v_val})"
            cv2.putText(frame, info, (10, 460),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            print(f"\r点击: ({x:4d},{y:4d})  BGR=({b:3d},{g:3d},{r:3d})  HSV=({h_val:3d},{s_val:3d},{v_val:3d})    ", end='', flush=True)
        
        cv2.imshow("Camera", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('s'):
            filename = f"snapshot_{int(cv2.getTickCount())}.jpg"
            cv2.imwrite(filename, frame)
            print(f"\n截图已保存: {filename}")
        elif key == ord('r'):
            show_cross = not show_cross
    
    cap.release()
    cv2.destroyAllWindows()
    print("\n摄像头已关闭")

if __name__ == "__main__":
    main()
