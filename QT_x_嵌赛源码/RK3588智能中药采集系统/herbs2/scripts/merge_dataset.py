#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并 baizhi + gouqi 单类数据集为双类 YOLO 数据集。

类别映射:
  0 = 白芷 (baizhi)
  1 = 枸杞 (gouqi)
负样本: 空 label，来自两工程 train 中的 neg_* 图片（去重合并）。
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BAIZHI = ROOT / "baizhi/dataset"
GOUQI = ROOT / "gouqi/dataset"
OUT = ROOT / "herbs2/dataset"
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def clear_split(split: str) -> None:
    for sub in ("images", "labels"):
        d = OUT / sub / split
        d.mkdir(parents=True, exist_ok=True)
        for p in d.iterdir():
            if p.is_file():
                p.unlink()
    for cache in (OUT / "labels" / f"{split}.cache",):
        if cache.exists():
            cache.unlink()


def read_label(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def remap_label(text: str, cls_id: int) -> str:
    if not text:
        return ""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        parts[0] = str(cls_id)
        out.append(" ".join(parts))
    return "\n".join(out) + ("\n" if out else "")


def copy_pair(
    img: Path,
    lbl: Path,
    img_dst: Path,
    lbl_dst: Path,
    cls_id: int | None,
    force_empty: bool = False,
) -> None:
    shutil.copy2(img, img_dst)
    if force_empty:
        lbl_dst.write_text("", encoding="utf-8")
        return
    text = read_label(lbl)
    if cls_id is None:
        lbl_dst.write_text(text + ("\n" if text else ""), encoding="utf-8")
    else:
        lbl_dst.write_text(remap_label(text, cls_id), encoding="utf-8")


def file_hash(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def merge_positives(src_root: Path, split: str, img_prefix: str, cls_id: int, skip_neg: bool = True) -> int:
    img_src = src_root / "images" / split
    lbl_src = src_root / "labels" / split
    img_dst = OUT / "images" / split
    lbl_dst = OUT / "labels" / split
    n = 0
    for img in sorted(img_src.iterdir()):
        if not img.is_file() or img.suffix.lower() not in IMG_EXTS:
            continue
        is_neg = img.stem.startswith("neg_")
        if skip_neg and is_neg:
            continue
        stem = f"{img_prefix}_{img.stem}"
        copy_pair(
            img,
            lbl_src / f"{img.stem}.txt",
            img_dst / f"{stem}{img.suffix.lower()}",
            lbl_dst / f"{stem}.txt",
            None if is_neg else cls_id,
            force_empty=is_neg,
        )
        n += 1
    return n


def merge_negatives() -> int:
    img_dst = OUT / "images" / "train"
    lbl_dst = OUT / "labels" / "train"
    seen: set[str] = set()
    n = 0
    for src_root, tag in ((BAIZHI, "bz"), (GOUQI, "gq")):
        img_src = src_root / "images" / "train"
        lbl_src = src_root / "labels" / "train"
        if not img_src.is_dir():
            continue
        for img in sorted(img_src.iterdir()):
            if not img.is_file() or img.suffix.lower() not in IMG_EXTS:
                continue
            if not img.stem.startswith("neg_"):
                continue
            digest = file_hash(img)
            if digest in seen:
                continue
            seen.add(digest)
            stem = f"neg_{tag}_{n:04d}"
            shutil.copy2(img, img_dst / f"{stem}{img.suffix.lower()}")
            text = read_label(lbl_src / f"{img.stem}.txt")
            (lbl_dst / f"{stem}.txt").write_text(text + ("\n" if text else ""), encoding="utf-8")
            n += 1
    return n


def main() -> None:
    if not BAIZHI.is_dir() or not GOUQI.is_dir():
        print("请先完成 baizhi、gouqi 单类数据导入后再合并。")
        sys.exit(1)

    clear_split("train")
    clear_split("val")

    bz_train = merge_positives(BAIZHI, "train", "bz", cls_id=0)
    gq_train = merge_positives(GOUQI, "train", "gq", cls_id=1)
    neg_n = merge_negatives()

    bz_val = merge_positives(BAIZHI, "val", "bz_val", cls_id=0, skip_neg=False)
    gq_val = merge_positives(GOUQI, "val", "gq_val", cls_id=1, skip_neg=False)

    print("双类数据集合并完成:")
    print(f"  train: 白芷={bz_train}, 枸杞={gq_train}, 负样本={neg_n}")
    print(f"  val  : 白芷侧={bz_val}, 枸杞侧={gq_val}")
    print(f"  输出 : {OUT}")


if __name__ == "__main__":
    main()
