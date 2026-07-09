#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ELF2 精确识别 — 数据准备：场景负样本 + 验证集负样本。

参考飞凌 ELF2 案例: 精确部署需覆盖真实场景负样本，降低端侧误检。

用法:
    python baizhi/scripts/prepare_precision_dataset.py --camera 0 --frames 50
    python baizhi/scripts/prepare_precision_dataset.py --import-herbs --per-class 5
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baizhi.scripts.import_hard_negatives import import_from_camera, import_from_herb_dataset, import_from_folder


def parse_args():
    p = argparse.ArgumentParser(description="Prepare precision dataset for ELF2 deployment")
    p.add_argument("--camera", type=int, default=-1)
    p.add_argument("--frames", type=int, default=50, help="采集场景负样本帧数")
    p.add_argument("--import-herbs", action="store_true", help="从100种中药导入 hard negative")
    p.add_argument("--per-class", type=int, default=5)
    p.add_argument("--source", type=str, default="", help="自定义负样本目录")
    return p.parse_args()


def main():
    args = parse_args()
    train_img = ROOT / "baizhi/dataset/images/train"
    train_lbl = ROOT / "baizhi/dataset/labels/train"
    val_img = ROOT / "baizhi/dataset/images/val"
    val_lbl = ROOT / "baizhi/dataset/labels/val"
    for d in [train_img, train_lbl, val_img, val_lbl]:
        d.mkdir(parents=True, exist_ok=True)

    total = 0
    if args.camera >= 0:
        n = import_from_camera(args.camera, args.frames, train_img, train_lbl)
        print(f"场景负样本: {n} 张")
        total += n

    if args.import_herbs:
        herb_base = Path(r"d:\中药材数据库\100种中药分类数据集\100种中药分类数据集\100种中药分类数据集\data")
        if herb_base.exists():
            total += import_from_herb_dataset(herb_base, train_img, train_lbl, args.per_class, 200)
        else:
            print("未找到100种中药数据集，跳过")

    if args.source:
        total += import_from_folder(Path(args.source), train_img, train_lbl, 100)

    # 复制部分负样本到 val（评估误检率）
    neg_train = sorted(train_img.glob("neg_*.jpg"))
    for i, src in enumerate(neg_train[:20]):
        dst = val_img / f"neg_val_{i:04d}.jpg"
        shutil.copy2(src, dst)
        (val_lbl / f"{dst.stem}.txt").write_text("", encoding="utf-8")

    pos = len([p for p in train_img.glob("baizhi_*.jpg")])
    neg = len([p for p in train_img.glob("neg_*.jpg")])
    print("=" * 60)
    print(f"数据集更新完成 | 白芷正样本: {pos} | 负样本: {neg} | 比例 1:{neg/max(pos,1):.1f}")
    print("下一步: python baizhi/scripts/train_elf2.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
