#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复制白芷实拍图 real_* 多份，避免被白底数据集淹没。"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMG_DIR = ROOT / "baizhi/dataset/images/train"
LBL_DIR = ROOT / "baizhi/dataset/labels/train"


def clear_boost(prefix: str = "real_boost_") -> int:
    n = 0
    for p in IMG_DIR.glob(f"{prefix}*.jpg"):
        p.unlink(missing_ok=True)
        n += 1
    for p in LBL_DIR.glob(f"{prefix}*.txt"):
        p.unlink(missing_ok=True)
    return n


def oversample(copies: int = 40, prefix: str = "real_boost_") -> int:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    LBL_DIR.mkdir(parents=True, exist_ok=True)
    sources = sorted(IMG_DIR.glob("real_[0-9]*.jpg"))
    if not sources:
        print("no real_*.jpg, run import_user_images.py first")
        return 0
    clear_boost(prefix)
    n = 0
    for src in sources:
        lbl = LBL_DIR / f"{src.stem}.txt"
        if not lbl.is_file():
            print(f"skip(no label): {src.name}")
            continue
        text = lbl.read_text(encoding="utf-8")
        for i in range(copies):
            name = f"{prefix}{src.stem}_{i:03d}"
            shutil.copy2(src, IMG_DIR / f"{name}.jpg")
            (LBL_DIR / f"{name}.txt").write_text(text, encoding="utf-8")
            n += 1
    cache = LBL_DIR / "train.cache"
    if cache.exists():
        cache.unlink()
    return n


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--copies", type=int, default=40)
    p.add_argument("--prefix", default="real_boost_")
    args = p.parse_args()
    n = oversample(args.copies, args.prefix)
    print(f"oversampled {n} images")


if __name__ == "__main__":
    main()
