#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导入用户提供的白芷实拍图到训练集（自动估计药片区域框）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
IMG_DIR = ROOT / "baizhi/dataset/images/train"
LBL_DIR = ROOT / "baizhi/dataset/labels/train"


def estimate_baizhi_box(bgr: np.ndarray) -> str:
    """用非白底区域估计白芷堆位置框。"""
    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(gray, 0, 238)
    bark = cv2.inRange(hsv, np.array([5, 15, 35]), np.array([30, 200, 230]))
    mask = cv2.bitwise_or(mask, bark)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    ys, xs = np.where(mask > 0)
    if len(xs) < 150:
        return "0 0.5 0.42 0.88 0.72\n"
    x1, x2 = xs.min(), xs.max()
    y1, y2 = ys.min(), ys.max()
    pad = int(max(x2 - x1, y2 - y1) * 0.06)
    x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
    x2, y2 = min(w - 1, x2 + pad), min(h - 1, y2 + pad)
    cx = (x1 + x2) / 2 / w
    cy = (y1 + y2) / 2 / h
    bw = (x2 - x1) / w
    bh = (y2 - y1) / h
    return f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n"


def import_images(sources: list[Path], prefix: str = "real") -> int:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    LBL_DIR.mkdir(parents=True, exist_ok=True)
    existing = len([p for p in IMG_DIR.glob(f"{prefix}_*.jpg") if "boost" not in p.stem])
    n = 0
    for src in sources:
        if not src.is_file():
            print(f"skip missing: {src}")
            continue
        bgr = cv2.imread(str(src))
        if bgr is None:
            print(f"skip unreadable: {src}")
            continue
        name = f"{prefix}_{existing + n:04d}.jpg"
        cv2.imwrite(str(IMG_DIR / name), bgr)
        label = estimate_baizhi_box(bgr)
        (LBL_DIR / f"{prefix}_{existing + n:04d}.txt").write_text(label, encoding="utf-8")
        print(f"import: {name} -> {label.strip()}")
        n += 1
    cache = LBL_DIR / "train.cache"
    if cache.exists():
        cache.unlink()
    return n


def main():
    p = argparse.ArgumentParser()
    p.add_argument("images", nargs="*", help="image paths")
    p.add_argument("--prefix", default="real")
    args = p.parse_args()

    if args.images:
        sources = [Path(x) for x in args.images]
    else:
        assets = Path(
            r"C:\Users\LWH\.cursor\projects\c-Users-LWH-Desktop-ultralytics-main\assets"
        )
        sources = sorted(assets.glob("*.png"))[-4:] if assets.exists() else []

    if not sources:
        print("usage: python baizhi/scripts/import_user_images.py img1.png img2.png")
        sys.exit(1)
    n = import_images(sources, args.prefix)
    print(f"imported {n} -> baizhi/dataset/images/train")


if __name__ == "__main__":
    main()
