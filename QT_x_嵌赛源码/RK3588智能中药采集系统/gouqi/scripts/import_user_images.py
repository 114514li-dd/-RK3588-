#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导入用户提供的枸杞实拍图到训练集（红色连通域自动标每颗枸杞）。"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
IMG_DIR = ROOT / "gouqi/dataset/images/train"
LBL_DIR = ROOT / "gouqi/dataset/labels/train"

QT1_ASSETS = Path(
    r"C:\Users\LWH\.cursor\projects\c-Users-LWH-Desktop-Q-boot-QT1\assets"
)
LEGACY_ASSETS = Path(
    r"C:\Users\LWH\.cursor\projects\c-Users-LWH-Desktop-ultralytics-main\assets"
)


def _cluster_box_label(bgr: np.ndarray) -> str:
    """整堆枸杞一个大框（兜底）。"""
    h, w = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array([0, 40, 40]), np.array([15, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([160, 40, 40]), np.array([180, 255, 255]))
    mask = cv2.bitwise_or(mask1, mask2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    ys, xs = np.where(mask > 0)
    if len(xs) < 100:
        return "0 0.5 0.48 0.58 0.58\n"
    x1, x2 = xs.min(), xs.max()
    y1, y2 = ys.min(), ys.max()
    pad = int(max(x2 - x1, y2 - y1) * 0.08)
    x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
    x2, y2 = min(w - 1, x2 + pad), min(h - 1, y2 + pad)
    cx = (x1 + x2) / 2 / w
    cy = (y1 + y2) / 2 / h
    bw = (x2 - x1) / w
    bh = (y2 - y1) / h
    return f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n"


def label_gouqi_berries(bgr: np.ndarray) -> str:
    """用红色掩膜 + 连通域为每颗枸杞生成 YOLO 框。"""
    h, w = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array([0, 30, 30]), np.array([20, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([150, 30, 30]), np.array([180, 255, 255]))
    mask = cv2.bitwise_or(mask1, mask2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.erode(mask, np.ones((3, 3), np.uint8), iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

    _, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    lines: list[str] = []
    min_area = max(40, (h * w) // 100000)

    for i in range(1, stats.shape[0]):
        x, y, bw, bh, area = stats[i]
        if area < min_area or area > (h * w) // 2:
            continue
        if bw < 3 or bh < 3:
            continue
        pad = 2
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(w - 1, x + bw + pad)
        y2 = min(h - 1, y + bh + pad)
        cx = (x1 + x2) / 2 / w
        cy = (y1 + y2) / 2 / h
        box_w = (x2 - x1) / w
        box_h = (y2 - y1) / h
        lines.append(f"0 {cx:.6f} {cy:.6f} {box_w:.6f} {box_h:.6f}")

    if len(lines) < 3:
        return _cluster_box_label(bgr)
    return "\n".join(lines) + "\n"


def discover_user_images() -> list[Path]:
    sources: list[Path] = []
    for folder in (QT1_ASSETS, LEGACY_ASSETS, ROOT.parent / "assets"):
        if not folder.is_dir():
            continue
        sources.extend(sorted(folder.glob("c__Users_*images_*.png")))
    if not sources:
        for folder in (QT1_ASSETS, LEGACY_ASSETS):
            if folder.is_dir():
                sources.extend(sorted(folder.glob("*.jpg")))
    # 去重
    seen: set[str] = set()
    unique: list[Path] = []
    for p in sources:
        key = p.name.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique


def import_images(sources: list[Path], prefix: str = "real") -> int:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    LBL_DIR.mkdir(parents=True, exist_ok=True)
    existing = len(list(IMG_DIR.glob(f"{prefix}_*.jpg")))
    n = 0
    for src in sources:
        if not src.is_file():
            print(f"跳过(不存在): {src}")
            continue
        bgr = cv2.imread(str(src))
        if bgr is None:
            print(f"跳过(无法读取): {src}")
            continue
        label_text = label_gouqi_berries(bgr)
        berry_count = len([ln for ln in label_text.strip().splitlines() if ln.strip()])
        name = f"{prefix}_{existing + n:04d}.jpg"
        cv2.imwrite(str(IMG_DIR / name), bgr)
        (LBL_DIR / f"{prefix}_{existing + n:04d}.txt").write_text(label_text, encoding="utf-8")
        print(f"导入: {name} ({berry_count} 框) <- {src.name}")
        n += 1
    cache = LBL_DIR / "train.cache"
    if cache.exists():
        cache.unlink()
    return n


def main():
    p = argparse.ArgumentParser()
    p.add_argument("images", nargs="*", help="图片路径，留空则扫描 QT1 assets")
    p.add_argument("--prefix", default="real")
    args = p.parse_args()

    if args.images:
        sources = [Path(x) for x in args.images]
    else:
        sources = discover_user_images()

    if not sources:
        print("未找到图片，用法: python gouqi/scripts/import_user_images.py 图1.jpg 图2.jpg")
        sys.exit(1)
    n = import_images(sources, args.prefix)
    print(f"共导入 {n} 张 -> gouqi/dataset/images/train")


if __name__ == "__main__":
    main()
