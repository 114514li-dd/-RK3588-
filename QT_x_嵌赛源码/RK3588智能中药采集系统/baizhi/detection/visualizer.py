"""检测结果可视化（OpenCV + 中文标签）。"""

from __future__ import annotations

import cv2
import numpy as np

from baizhi.scripts.utils_plot import draw_chinese_boxes, shrink_boxes_xyxy

from .config import BaizhiDetectConfig
from .types import BaizhiBox, BaizhiDetectResult


def draw_result(
    frame_bgr: np.ndarray,
    result: BaizhiDetectResult,
    cfg: BaizhiDetectConfig,
) -> np.ndarray:
    """在 BGR 图像上绘制检测框与中文标签。"""
    if not cfg.draw_labels or result.count == 0:
        return frame_bgr

    xyxy = np.array([b.bbox_xyxy() for b in result.boxes], dtype=np.float32)
    if len(xyxy) == 0:
        return frame_bgr

    xyxy = shrink_boxes_xyxy(xyxy, cfg.box_shrink, frame_bgr.shape)
    labels = [f"{b.class_name} {b.confidence:.2f}" for b in result.boxes]
    return draw_chinese_boxes(frame_bgr, xyxy, labels)


def draw_status_bar(
    frame_bgr: np.ndarray,
    result: BaizhiDetectResult,
    fps: float = 0.0,
    extra: str = "",
) -> np.ndarray:
    """绘制顶部状态栏：数量、FPS。"""
    text = f"白芷 x{result.count}"
    if fps > 0:
        text += f" | {fps:.1f}fps"
    if extra:
        text += f" | {extra}"
    cv2.putText(frame_bgr, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
    return frame_bgr
