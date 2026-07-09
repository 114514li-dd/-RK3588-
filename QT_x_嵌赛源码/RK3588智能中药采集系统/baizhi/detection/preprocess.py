"""OpenCV 图像读取与轻量预处理（不含传统阈值/轮廓检测）。"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .config import BaizhiDetectConfig


def load_image(path: str | Path) -> np.ndarray | None:
    """读取 BGR 图像，失败返回 None。"""
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None or img.size == 0:
        return None
    return img


def preprocess_frame(frame_bgr: np.ndarray, cfg: BaizhiDetectConfig) -> np.ndarray:
    """可选 CLAHE 对比度增强，改善模糊/低对比度画面；不改变检测算法本身。"""
    if not cfg.enhance_contrast:
        return frame_bgr

    lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=cfg.clahe_clip, tileGridSize=(8, 8))
    l = clahe.apply(l)
    merged = cv2.merge([l, a, b])
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def resize_for_display(frame_bgr: np.ndarray, max_side: int = 1280) -> np.ndarray:
    """仅用于显示缩放，不参与推理。"""
    h, w = frame_bgr.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    if scale >= 1.0:
        return frame_bgr
    nw, nh = int(w * scale), int(h * scale)
    return cv2.resize(frame_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)


def image_shape(frame_bgr: np.ndarray) -> tuple[int, int]:
    h, w = frame_bgr.shape[:2]
    return w, h
