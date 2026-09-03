"""
OpenCV物体检测模块
功能：检测摄像头画面中的物体，返回物体位置和大小
支持：颜色检测、形状检测
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional


class ObjectDetector:
    """物体检测器，支持颜色和形状检测"""

    def __init__(self):
        # 颜色范围（HSV）
        self.color_ranges = {
            'red': {
                'lower1': np.array([0, 100, 100]),
                'upper1': np.array([10, 255, 255]),
                'lower2': np.array([170, 100, 100]),
                'upper2': np.array([180, 255, 255])
            },
            'blue': {
                'lower': np.array([100, 100, 100]),
                'upper': np.array([130, 255, 255])
            },
            'green': {
                'lower': np.array([40, 100, 100]),
                'upper': np.array([80, 255, 255])
            },
            'yellow': {
                'lower': np.array([20, 100, 100]),
                'upper': np.array([35, 255, 255])
            }
        }

        # 检测参数
        self.min_area = 500  # 最小检测面积
        self.max_area = 50000  # 最大检测面积

    def detect_by_color(self, frame: np.ndarray, color: str = 'red') -> List[Dict]:
        """
        按颜色检测物体
        :param frame: BGR图像
        :param color: 颜色名称（red, blue, green, yellow）
        :return: 检测到的物体列表
        """
        if color not in self.color_ranges:
            print(f"[WARN] 未知颜色: {color}")
            return []

        # 转换到HSV颜色空间
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 创建颜色掩码
        if color == 'red':
            # 红色需要两个范围
            mask1 = cv2.inRange(hsv, self.color_ranges['red']['lower1'], self.color_ranges['red']['upper1'])
            mask2 = cv2.inRange(hsv, self.color_ranges['red']['lower2'], self.color_ranges['red']['upper2'])
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            mask = cv2.inRange(hsv, self.color_ranges[color]['lower'], self.color_ranges[color]['upper'])

        # 形态学操作（去噪）
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_area < area < self.max_area:
                # 计算外接矩形
                x, y, w, h = cv2.boundingRect(contour)
                # 计算中心点
                cx = x + w // 2
                cy = y + h // 2

                objects.append({
                    'color': color,
                    'center': (cx, cy),
                    'bbox': (x, y, w, h),
                    'area': area,
                    'aspect_ratio': w / h if h > 0 else 0
                })

        # 按面积排序（大的在前）
        objects.sort(key=lambda x: x['area'], reverse=True)
        return objects

    def detect_all_colors(self, frame: np.ndarray) -> List[Dict]:
        """
        检测所有支持的颜色
        :param frame: BGR图像
        :return: 所有检测到的物体
        """
        all_objects = []
        for color in self.color_ranges.keys():
            objects = self.detect_by_color(frame, color)
            all_objects.extend(objects)

        # 按面积排序
        all_objects.sort(key=lambda x: x['area'], reverse=True)
        return all_objects

    def draw_detections(self, frame: np.ndarray, objects: List[Dict]) -> np.ndarray:
        """
        在图像上绘制检测结果
        :param frame: 原始图像
        :param objects: 检测到的物体列表
        :return: 标注后的图像
        """
        result = frame.copy()

        # 颜色对应BGR值
        color_bgr = {
            'red': (0, 0, 255),
            'blue': (255, 0, 0),
            'green': (0, 255, 0),
            'yellow': (0, 255, 255)
        }

        for i, obj in enumerate(objects):
            x, y, w, h = obj['bbox']
            cx, cy = obj['center']
            color = obj['color']
            bgr = color_bgr.get(color, (255, 255, 255))

            # 绘制矩形框
            cv2.rectangle(result, (x, y), (x + w, y + h), bgr, 2)

            # 绘制中心点
            cv2.circle(result, (cx, cy), 5, bgr, -1)

            # 绘制标签
            label = f"{color}_{i} ({cx},{cy})"
            cv2.putText(result, label, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, bgr, 2)

        return result

    def pixel_to_arm_coords(self, pixel_x: int, pixel_y: int,
                            frame_width: int = 640, frame_height: int = 480) -> Tuple[float, float]:
        """
        将像素坐标转换为机械臂坐标（简化版）
        :param pixel_x: 像素x坐标
        :param pixel_y: 像素y坐标
        :param frame_width: 图像宽度
        :param frame_height: 图像高度
        :return: (arm_x, arm_y) 机械臂坐标系下的位置
        """
        # 将像素坐标归一化到-1到1
        norm_x = (pixel_x - frame_width / 2) / (frame_width / 2)
        norm_y = (pixel_y - frame_height / 2) / (frame_height / 2)

        # 转换到机械臂坐标系（需要根据实际标定调整）
        # 这里使用简单的线性映射
        arm_x = norm_x * 30  # 左右范围±30度
        arm_y = -norm_y * 30  # 上下范围±30度（y轴反转）

        return arm_x, arm_y


def test_detector():
    """测试检测器"""
    detector = ObjectDetector()

    # 打开摄像头
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return

    print("[INFO] 物体检测测试")
    print("[INFO] 按 'q' 退出，按 'c' 切换检测颜色")

    detect_color = 'all'  # all, red, blue, green, yellow

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 检测物体
        if detect_color == 'all':
            objects = detector.detect_all_colors(frame)
        else:
            objects = detector.detect_by_color(frame, detect_color)

        # 绘制检测结果
        result = detector.draw_detections(frame, objects)

        # 显示信息
        info_text = f"Detect: {detect_color} | Found: {len(objects)} | Press 'q' quit, 'c' change"
        cv2.putText(result, info_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # 显示最大物体的坐标
        if objects:
            largest = objects[0]
            cx, cy = largest['center']
            arm_x, arm_y = detector.pixel_to_arm_coords(cx, cy)
            coord_text = f"Largest: {largest['color']} at ({cx},{cy}) -> arm({arm_x:.1f}, {arm_y:.1f})"
            cv2.putText(result, coord_text, (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        cv2.imshow('Object Detection', result)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            # 切换检测颜色
            colors = ['all', 'red', 'blue', 'green', 'yellow']
            idx = colors.index(detect_color)
            detect_color = colors[(idx + 1) % len(colors)]
            print(f"[INFO] 切换到: {detect_color}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    test_detector()
