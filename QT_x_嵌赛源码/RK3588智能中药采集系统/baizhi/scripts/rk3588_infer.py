#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RK3588 板端 RKNN 推理示例（需在 RK3588 上运行，安装 rknnlite2）。

用法:
    python baizhi/scripts/rk3588_infer.py --rknn baizhi/weights/rknn/best-rk3588.rknn --source test.jpg
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RK3588 RKNN inference demo for Bai Zhi")
    parser.add_argument("--rknn", type=str, required=True)
    parser.add_argument("--source", type=str, required=True)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.25)
    return parser.parse_args()


def nms(boxes: np.ndarray, scores: np.ndarray, iou_thresh: float = 0.45) -> list[int]:
    x1, y1, x2, y2 = boxes.T
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size:
        i = order[0]
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0, xx2 - xx1)
        h = np.maximum(0, yy2 - yy1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        order = order[1:][iou <= iou_thresh]
    return keep


def main() -> None:
    args = parse_args()
    try:
        from rknnlite.api import RKNNLite
    except ImportError as e:
        raise ImportError("请在 RK3588 板端安装 rknnlite2: pip install rknnlite2") from e

    rknn = RKNNLite()
    if rknn.load_rknn(args.rknn) != 0:
        raise RuntimeError("load_rknn failed")
    if rknn.init_runtime() != 0:
        raise RuntimeError("init_runtime failed")

    img = cv2.imread(args.source)
    if img is None:
        raise FileNotFoundError(args.source)
    h0, w0 = img.shape[:2]
    img_in = cv2.resize(img, (args.imgsz, args.imgsz))
    img_rgb = cv2.cvtColor(img_in, cv2.COLOR_BGR2RGB)
    outputs = rknn.inference(inputs=[np.expand_dims(img_rgb, 0)])

    # YOLOv8 RKNN 输出格式依导出配置而定，此处为通用后处理占位
    # 生产环境建议使用 Ultralytics RKNNBackend 或官方 rknn_model_zoo YOLOv8 demo
    print(f"RKNN 推理完成，输出 tensor 数: {len(outputs)}")
    print("后处理请对接导出 metadata 中的 stride/conf/iou 参数，或使用 ultralytics RKNNBackend")

    rknn.release()


if __name__ == "__main__":
    main()
