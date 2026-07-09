#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导入其他药材作为枸杞检测负样本（含白芷，降低混淆）。"""

from __future__ import annotations

import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERB_BASE = Path(r"d:\中药材数据库\100种中药分类数据集\100种中药分类数据集\100种中药分类数据集\data")
SKIP = {"枸杞子", "枸杞"}
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main():
    train_img = ROOT / "gouqi/dataset/images/train"
    train_lbl = ROOT / "gouqi/dataset/labels/train"
    train_img.mkdir(parents=True, exist_ok=True)
    train_lbl.mkdir(parents=True, exist_ok=True)
    n = 0
    classes = [p for p in (HERB_BASE / "train").iterdir() if p.is_dir() and p.name not in SKIP]
    random.shuffle(classes)
    for cls in classes:
        imgs = [p for p in cls.iterdir() if p.suffix.lower() in IMG_EXTS]
        random.shuffle(imgs)
        for src in imgs[:3]:
            name = f"neg_{cls.name[:6]}_{n:04d}{src.suffix.lower()}"
            shutil.copy2(src, train_img / name)
            (train_lbl / f"{Path(name).stem}.txt").write_text("", encoding="utf-8")
            n += 1
            if n >= 150:
                print(f"负样本导入 {n} 张")
                return
    print(f"负样本导入 {n} 张")


if __name__ == "__main__":
    main()
