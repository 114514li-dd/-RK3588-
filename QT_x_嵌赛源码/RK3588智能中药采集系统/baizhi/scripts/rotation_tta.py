#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多角度推理：解决摄像头/平板横竖屏导致枸杞置信度极低的问题。"""

from __future__ import annotations

import cv2
import numpy as np


def rotate_frame(frame: np.ndarray, k: int) -> np.ndarray:
    if k == 0:
        return frame
    if k == 1:
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    if k == 2:
        return cv2.rotate(frame, cv2.ROTATE_180)
    if k == 3:
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    raise ValueError(k)


def map_boxes_to_original(xyxy: np.ndarray, k: int, orig_shape: tuple) -> np.ndarray:
    """将旋转图上的 xyxy 映射回原图坐标。"""
    if k == 0 or len(xyxy) == 0:
        return xyxy
    h, w = orig_shape[:2]
    out = xyxy.copy().astype(np.float32)
    for i, (x1, y1, x2, y2) in enumerate(out):
        if k == 1:  # 90° CW
            nx1, ny1 = y1, h - x2
            nx2, ny2 = y2, h - x1
        elif k == 2:
            nx1, ny1 = w - x2, h - y2
            nx2, ny2 = w - x1, h - y1
        else:  # 90° CCW
            nx1, ny1 = w - y2, x1
            nx2, ny2 = w - y1, x2
        out[i] = [min(nx1, nx2), min(ny1, ny2), max(nx1, nx2), max(ny1, ny2)]
    out[:, [0, 2]] = np.clip(out[:, [0, 2]], 0, w)
    out[:, [1, 3]] = np.clip(out[:, [1, 3]], 0, h)
    return out


def _box_iou(a: np.ndarray, b: np.ndarray) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0:
        return 0.0
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def nms_keep_best(xyxy: np.ndarray, conf: np.ndarray, iou_thr: float = 0.45) -> np.ndarray:
    """重叠框合并，保留置信度最高者。"""
    if len(xyxy) == 0:
        return np.array([], dtype=int)
    order = conf.argsort()[::-1]
    keep: list[int] = []
    while len(order):
        i = int(order[0])
        keep.append(i)
        if len(order) == 1:
            break
        rest = order[1:]
        remain = [j for j in rest if _box_iou(xyxy[i], xyxy[j]) < iou_thr]
        order = np.array(remain, dtype=int) if remain else np.array([], dtype=int)
    return np.array(keep, dtype=int)


def predict_with_rotation(model, frame, predict_once, enable: bool = True, iou_merge: float = 0.45):
    """四方向推理后 NMS 合并，同一目标取各方向最高置信度。"""
    all_xy, all_cf, all_cl = [], [], []
    rotations = range(4) if enable else (0,)
    for k in rotations:
        rot = rotate_frame(frame, k)
        result = predict_once(model, rot)
        if result is None:
            continue
        xy, cf, cl = result
        xy = map_boxes_to_original(xy, k, frame.shape)
        all_xy.append(xy)
        all_cf.append(cf)
        all_cl.append(cl)
    if not all_xy:
        return None
    xy = np.concatenate(all_xy)
    cf = np.concatenate(all_cf)
    cl = np.concatenate(all_cl)
    keep = nms_keep_best(xy, cf, iou_merge)
    return xy[keep], cf[keep], cl[keep]
