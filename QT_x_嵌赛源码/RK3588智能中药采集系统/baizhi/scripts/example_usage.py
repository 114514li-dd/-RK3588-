#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""白芷 YOLOv8 + OpenCV 检测管线 — 调用示例。

运行（在 ultralytics-main 根目录）:
    python baizhi/scripts/example_usage.py
    python baizhi/scripts/example_usage.py --image path/to/test.jpg
    python baizhi/scripts/example_usage.py --camera
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baizhi.detection import BaizhiDetectConfig, BaizhiDetector, run_camera_loop


def example_single_image(image_path: str) -> None:
    """示例 1：单图检测，获取坐标/置信度/数量。"""
    cfg = BaizhiDetectConfig.balanced(conf=0.55)
    detector = BaizhiDetector(cfg)
    result = detector.detect_image(image_path)

    print("=== 单图检测 ===")
    print(f"成功: {result.success}, 数量: {result.count}")
    for i, box in enumerate(result.boxes, 1):
        x, y, w, h = box.bbox_xywh()
        print(
            f"  [{i}] {box.class_name} conf={box.confidence:.3f} "
            f"xyxy=({box.x1},{box.y1},{box.x2},{box.y2}) "
            f"xywh=({x},{y},{w},{h})"
        )

    # 兼容 Qt HerbDetectItem 风格
    print("\n=== Qt 业务兼容格式 ===")
    for box in result.boxes:
        x, y, w, h = box.bbox_xywh()
        print(f'  name="{box.class_name}" confidence={box.confidence:.3f} bbox=QRect({x},{y},{w},{h})')

    print("\n=== JSON ===")
    print(result.to_json(indent=2))


def example_detect_and_draw(image_path: str, save_path: str) -> None:
    """示例 2：检测 + OpenCV 可视化保存。"""
    import cv2

    cfg = BaizhiDetectConfig.strict()
    detector = BaizhiDetector(cfg)
    img = cv2.imread(image_path)
    if img is None:
        print(f"无法读取: {image_path}")
        return

    result, vis = detector.detect_and_draw(img)
    cv2.imwrite(save_path, vis)
    print(f"检测 {result.count} 个白芷，已保存: {save_path}")


def example_camera() -> None:
    """示例 3：摄像头实时检测（含跳帧、连续帧确认）。"""
    cfg = BaizhiDetectConfig.balanced(max_fps=10, confirm_frames=2)
    detector = BaizhiDetector(cfg)
    print("摄像头检测启动，按 Q 退出…")
    run_camera_loop(detector)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Baizhi detection usage examples")
    p.add_argument("--image", type=str, default="", help="测试图片路径")
    p.add_argument("--save", type=str, default=str(ROOT / "baizhi/runs/detect/example_out.jpg"))
    p.add_argument("--camera", action="store_true", help="运行摄像头示例")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.camera:
        example_camera()
        return

    # 默认找一张验证集图片
    image = args.image
    if not image:
        val_dir = ROOT / "baizhi/dataset/images/val"
        if val_dir.exists():
            candidates = list(val_dir.glob("*.jpg")) + list(val_dir.glob("*.png"))
            if candidates:
                image = str(candidates[0])

    if not image or not Path(image).exists():
        print("请指定 --image 路径，或确保 baizhi/dataset/images/val 下有图片")
        print("\n模块结构:")
        print("  baizhi/detection/preprocess.py   — OpenCV 读取与轻量预处理")
        print("  baizhi/detection/inferencer.py   — YOLOv8 推理（conf + NMS）")
        print("  baizhi/detection/postprocess.py  — 结果解析与业务过滤")
        print("  baizhi/detection/visualizer.py   — 框选绘制")
        print("  baizhi/detection/pipeline.py     — BaizhiDetector 统一入口")
        print("  baizhi/detection/video_stream.py   — 视频流/摄像头")
        return

    example_single_image(image)
    example_detect_and_draw(image, args.save)


if __name__ == "__main__":
    main()
