#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为枸杞训练集添加 90/180/270 旋转副本，提升旋转场景置信度。"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
IMG_DIR = ROOT / "gouqi/dataset/images/train"
LBL_DIR = ROOT / "gouqi/dataset/labels/train"
ROTS = {
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def main() -> None:
    n = 0
    for img in sorted(IMG_DIR.glob("gouqi_*.jpg")):
        lbl = LBL_DIR / f"{img.stem}.txt"
        if not lbl.exists():
            continue
        text = lbl.read_text(encoding="utf-8")
        frame = cv2.imread(str(img))
        if frame is None:
            continue
        for deg, flag in ROTS.items():
            stem = f"{img.stem}_r{deg}"
            out_img = IMG_DIR / f"{stem}.jpg"
            if out_img.exists():
                continue
            cv2.imwrite(str(out_img), cv2.rotate(frame, flag))
            (LBL_DIR / f"{stem}.txt").write_text(text, encoding="utf-8")
            n += 1
    cache = LBL_DIR / "train.cache"
    if cache.exists():
        cache.unlink()
    print(f"旋转增强: 新增 {n} 张 (gouqi_*_r90/r180/r270)")


if __name__ == "__main__":
    main()
