#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中文检测框绘制工具（OpenCV 不支持中文，使用 Pillow）。"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


_font_cache: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _get_font(size: int = 20) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if size not in _font_cache:
        candidates = [
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/System/Library/Fonts/PingFang.ttc",
        ]
        for p in candidates:
            if Path(p).exists():
                _font_cache[size] = ImageFont.truetype(p, size)
                break
        else:
            _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]


def shrink_boxes_xyxy(
    boxes: np.ndarray,
    scale: float,
    img_shape: tuple[int, int] | None = None,
) -> np.ndarray:
    """向中心收缩检测框，scale=0.65 表示宽高各缩至 65%（仅影响显示）。"""
    if scale >= 1.0 or len(boxes) == 0:
        return boxes
    out = boxes.copy().astype(np.float32)
    for i, (x1, y1, x2, y2) in enumerate(out):
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        w, h = (x2 - x1) * scale, (y2 - y1) * scale
        out[i] = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
    if img_shape is not None:
        h, w = img_shape[:2]
        out[:, [0, 2]] = np.clip(out[:, [0, 2]], 0, w)
        out[:, [1, 3]] = np.clip(out[:, [1, 3]], 0, h)
    return out


def draw_chinese_boxes(
    img_bgr: np.ndarray,
    boxes_xyxy: np.ndarray,
    labels: list[str],
    color: tuple[int, int, int] = (0, 180, 0),
    thickness: int = 2,
) -> np.ndarray:
    """在 BGR 图像上绘制矩形框与中文标签。"""
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil)
    font = _get_font(22)

    for box, text in zip(boxes_xyxy, labels):
        x1, y1, x2, y2 = map(int, box)
        draw.rectangle([x1, y1, x2, y2], outline=color, width=thickness)
        tw, th = draw.textbbox((0, 0), text, font=font)[2:]
        ty = max(y1 - th - 6, 0)
        draw.rectangle([x1, ty, x1 + tw + 8, ty + th + 6], fill=color)
        draw.text((x1 + 4, ty + 2), text, fill=(255, 255, 255), font=font)

    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
