"""
YOLOv8 物体检测脚本
用YOLOv8实时检测摄像头画面中的物体，框住并标注

YOLOv8可以检测80种常见物体:
  person(人), bottle(瓶子), cup(杯子), apple(苹果), banana(香蕉),
  book(书), cell phone(手机), scissors(剪刀), fork(叉子), knife(刀)等

用法:
  python yolo_detect.py              # 默认摄像头0
  python yolo_detect.py 1            # 指定摄像头
  python yolo_detect.py 0 --conf 0.5 # 指定置信度阈值

首次运行会自动下载yolov8n.pt模型（约6MB）
"""
import cv2
import sys
import os
import numpy as np
import torch
from ultralytics import YOLO

# COCO 80类物体名称
COCO_CLASSES = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
    'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
    'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
    'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
    'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
    'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
    'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
    'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
    'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
    'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
    'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear',
    'hair drier', 'toothbrush'
]

# 常见可抓取物体（建议检测这些）
GRASPABLE = {'bottle', 'cup', 'apple', 'banana', 'orange', 'book', 'cell phone',
             'scissors', 'fork', 'knife', 'spoon', 'bowl', 'remote', 'teddy bear',
             'sports ball', 'vase'}

# 每个类别一个颜色（生成固定颜色）
np.random.seed(42)
COLORS = np.random.randint(50, 255, size=(80, 3), dtype=np.uint8)

def main():
    cam_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    conf_threshold = 0.4
    
    # 解析命令行参数
    if '--conf' in sys.argv:
        idx = sys.argv.index('--conf')
        if idx + 1 < len(sys.argv):
            conf_threshold = float(sys.argv[idx + 1])
    
    print("=" * 60)
    print("YOLOv8 物体检测")
    print("=" * 60)
    
    # 加载模型（使用GPU加速）
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\n加载YOLOv8模型 (device={device})...")
    model = YOLO('yolov8n.pt')
    print(f"✓ 模型已加载，使用 {'GPU: ' + torch.cuda.get_device_name(0) if device == 'cuda' else 'CPU'}")
    
    # 打开摄像头
    cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"无法打开摄像头 {cam_id}")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print(f"\n摄像头: {cam_id}")
    print(f"置信度阈值: {conf_threshold}")
    print()
    print("操作说明:")
    print("  q/Esc  - 退出")
    print("  s      - 截图")
    print("  f      - 只显示可抓取物体 / 全部物体")
    print("  +/-    - 调整置信度阈值")
    print()
    
    graspable_only = False
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # YOLO检测
        results = model(frame, conf=conf_threshold, verbose=False, device=device)
        
        detections = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = COCO_CLASSES[cls_id]
                
                if graspable_only and cls_name not in GRASPABLE:
                    continue
                
                detections.append({
                    'bbox': (x1, y1, x2, y2),
                    'conf': conf,
                    'class': cls_name,
                    'cls_id': cls_id,
                    'center': ((x1+x2)//2, (y1+y2)//2),
                    'area': (x2-x1) * (y2-y1),
                })
        
        # 绘制检测结果
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            cls_name = det['class']
            conf = det['conf']
            cls_id = det['cls_id']
            color = COLORS[cls_id].tolist()
            
            # 画框
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # 标签背景
            label = f"{cls_name} {conf:.2f}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
            cv2.putText(frame, label, (x1, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # 中心点
            cx, cy = det['center']
            cv2.circle(frame, (cx, cy), 4, color, -1)
            
            # 可抓取物体标记
            if cls_name in GRASPABLE:
                cv2.putText(frame, "GRASP", (x1, y2 + 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        # 画面中心十字
        h, w = frame.shape[:2]
        cv2.line(frame, (w//2-15, h//2), (w//2+15, h//2), (0, 255, 0), 1)
        cv2.line(frame, (w//2, h//2-15), (w//2, h//2+15), (0, 255, 0), 1)
        
        # 状态信息
        info = f"Objects: {len(detections)} | Conf: {conf_threshold:.2f} | Mode: {'Graspable' if graspable_only else 'All'}"
        cv2.putText(frame, info, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 显示最大物体信息
        if detections:
            best = max(detections, key=lambda x: x['area'])
            cx, cy = best['center']
            cv2.putText(frame, f"Best: {best['class']} ({cx},{cy}) A={best['area']}",
                        (10, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        cv2.imshow("YOLO Detection", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('s'):
            cv2.imwrite("yolo_snapshot.jpg", frame)
            print("截图已保存: yolo_snapshot.jpg")
        elif key == ord('f'):
            graspable_only = not graspable_only
            print(f"模式: {'只显示可抓取物体' if graspable_only else '显示全部物体'}")
        elif key == ord('+') or key == ord('='):
            conf_threshold = min(0.95, conf_threshold + 0.05)
            print(f"置信度: {conf_threshold:.2f}")
        elif key == ord('-'):
            conf_threshold = max(0.05, conf_threshold - 0.05)
            print(f"置信度: {conf_threshold:.2f}")
    
    cap.release()
    cv2.destroyAllWindows()
    print("已关闭")

if __name__ == "__main__":
    main()
