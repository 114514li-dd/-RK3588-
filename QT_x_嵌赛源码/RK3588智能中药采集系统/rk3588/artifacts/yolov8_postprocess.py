"""YOLOv8 单类检测 RKNN 后处理 (nc=1)。"""

from __future__ import annotations

import numpy as np


def _xywh2xyxy(x: np.ndarray) -> np.ndarray:
    y = np.empty_like(x)
    y[:, 0] = x[:, 0] - x[:, 2] / 2
    y[:, 1] = x[:, 1] - x[:, 3] / 2
    y[:, 2] = x[:, 0] + x[:, 2] / 2
    y[:, 3] = x[:, 1] + x[:, 3] / 2
    return y


def nms(boxes: np.ndarray, scores: np.ndarray, iou_thresh: float = 0.45) -> list[int]:
    x1, y1, x2, y2 = boxes.T
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        order = order[1:][iou <= iou_thresh]
    return keep


def scale_boxes(boxes: np.ndarray, img_shape: tuple[int, int], input_size: int) -> np.ndarray:
    """将 letterbox 坐标映射回原图。"""
    h, w = img_shape
    gain = min(input_size / h, input_size / w)
    pad_x = (input_size - w * gain) / 2
    pad_y = (input_size - h * gain) / 2
    boxes[:, [0, 2]] = (boxes[:, [0, 2]] - pad_x) / gain
    boxes[:, [1, 3]] = (boxes[:, [1, 3]] - pad_y) / gain
    boxes[:, 0::2] = boxes[:, 0::2].clip(0, w)
    boxes[:, 1::2] = boxes[:, 1::2].clip(0, h)
    return boxes


def postprocess_yolov8(
    outputs: list[np.ndarray],
    conf_thres: float = 0.75,
    iou_thres: float = 0.45,
    nc: int = 1,
    max_det: int = 10,
) -> tuple[np.ndarray, np.ndarray]:
    """解析 YOLOv8 RKNN 输出 -> boxes(xyxy), scores。"""
    pred = outputs[0]
    if pred.ndim == 3:
        pred = pred[0]
    if pred.shape[0] == 4 + nc:
        pred = pred.T
    boxes_xywh = pred[:, :4]
    if nc == 1:
        scores = pred[:, 4]
    else:
        cls_scores = pred[:, 4 : 4 + nc]
        scores = cls_scores.max(axis=1)
    mask = scores >= conf_thres
    boxes_xywh = boxes_xywh[mask]
    scores = scores[mask]
    if len(scores) == 0:
        return np.zeros((0, 4)), np.zeros((0,))
    boxes = _xywh2xyxy(boxes_xywh)
    keep = nms(boxes, scores, iou_thres)[:max_det]
    return boxes[keep], scores[keep]


def filter_by_area(
    boxes: np.ndarray,
    scores: np.ndarray,
    img_shape: tuple[int, int],
    min_ratio: float = 0.015,
    max_ratio: float = 0.85,
) -> tuple[np.ndarray, np.ndarray]:
    if len(boxes) == 0:
        return boxes, scores
    h, w = img_shape
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1]) / (h * w)
    keep = (areas >= min_ratio) & (areas <= max_ratio) if max_ratio > 0 else areas >= min_ratio
    return boxes[keep], scores[keep]
