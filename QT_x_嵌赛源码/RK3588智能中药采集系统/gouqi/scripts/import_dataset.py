#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 100种中药分类数据集 导入枸杞子训练/验证集。"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERB_SRC = Path(
    r"d:\中药材数据库\100种中药分类数据集\100种中药分类数据集\100种中药分类数据集\data"
)
HERB_FOLDER = "枸杞子"
TRAIN_SRC = HERB_SRC / "train" / HERB_FOLDER
VAL_SRC = HERB_SRC / "val" / HERB_FOLDER
LABEL_LINE = "0 0.5 0.5 1.0 1.0\n"  # 初始整图框，建议后续 LabelImg 精修
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def clear_dir(d: Path) -> None:
    if not d.exists():
        return
    for p in d.iterdir():
        if p.is_file():
            p.unlink()


def import_split(src_dir: Path, img_dir: Path, lbl_dir: Path, prefix: str, clear: bool = False) -> int:
    if not src_dir.is_dir():
        raise FileNotFoundError(f"源目录不存在: {src_dir}")
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    if clear:
        clear_dir(img_dir)
        clear_dir(lbl_dir)
    files = sorted([p for p in src_dir.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXTS])
    for i, src in enumerate(files):
        name = f"{prefix}_{i:04d}{src.suffix.lower()}"
        shutil.copy2(src, img_dir / name)
        (lbl_dir / f"{Path(name).stem}.txt").write_text(LABEL_LINE, encoding="utf-8")
    return len(files)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=str, default=str(HERB_SRC), help="数据集根目录")
    parser.add_argument("--train-src", type=str, default="", help="训练集源目录，默认 src/train/枸杞子")
    parser.add_argument("--val-src", type=str, default="", help="验证集源目录，默认 src/val/枸杞子")
    parser.add_argument("--train-only", action="store_true")
    parser.add_argument("--val-only", action="store_true")
    args = parser.parse_args()

    base = Path(args.src)
    train_src = Path(args.train_src) if args.train_src else base / "train" / HERB_FOLDER
    val_src = Path(args.val_src) if args.val_src else base / "val" / HERB_FOLDER

    train_n, val_n = 0, 0
    if not args.val_only:
        train_n = import_split(
            train_src,
            ROOT / "gouqi/dataset/images/train",
            ROOT / "gouqi/dataset/labels/train",
            "gouqi",
            clear=False,
        )
    if not args.train_only:
        val_n = import_split(
            val_src,
            ROOT / "gouqi/dataset/images/val",
            ROOT / "gouqi/dataset/labels/val",
            "gouqi_val",
            clear=True,
        )
        val_cache = ROOT / "gouqi/dataset/labels/val.cache"
        if val_cache.exists():
            val_cache.unlink()

    print(f"枸杞数据集导入完成: train={train_n}, val={val_n}")
    print(f"  train 源: {train_src}")
    print(f"  val   源: {val_src}")
    print(f"  输出: {ROOT / 'gouqi/dataset'}")


if __name__ == "__main__":
    main()
