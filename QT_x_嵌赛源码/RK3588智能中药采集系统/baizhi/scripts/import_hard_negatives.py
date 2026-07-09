#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导入负样本（无白芷图片）— 解决摄像头/场景误检。

YOLO 负样本规则: 图片放入 images/train，对应 labels/train 下创建**空** .txt 文件。

用法:
    # 从 100种中药数据集导入其他药材作为 hard negative（推荐）
    python baizhi/scripts/import_hard_negatives.py --per-class 5

    # 从任意文件夹导入
    python baizhi/scripts/import_hard_negatives.py --source D:/photos/room --max 50

    # 从摄像头采集 30 帧负样本
    python baizhi/scripts/import_hard_negatives.py --camera 0 --frames 30
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
HERB_DATASET = Path(
    r"d:\中药材数据库\100种中药分类数据集\100种中药分类数据集\100种中药分类数据集\data"
)
BAIZHI_NAME = "白芷"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Import negative samples for Bai Zhi detector")
    p.add_argument("--source", type=str, default="", help="自定义负样本图片目录")
    p.add_argument("--herb-dataset", type=str, default=str(HERB_DATASET), help="100种中药数据集根目录")
    p.add_argument("--per-class", type=int, default=5, help="每类易混淆药材采样张数")
    p.add_argument("--max", type=int, default=200, help="最多导入张数")
    p.add_argument("--camera", type=int, default=-1, help="摄像头索引，>=0 时从摄像头采集")
    p.add_argument("--frames", type=int, default=30, help="摄像头采集帧数")
    p.add_argument("--split", type=str, default="train", choices=["train", "val"])
    return p.parse_args()


def dst_dirs(split: str) -> tuple[Path, Path]:
    img = ROOT / "baizhi/dataset/images" / split
    lbl = ROOT / "baizhi/dataset/labels" / split
    img.mkdir(parents=True, exist_ok=True)
    lbl.mkdir(parents=True, exist_ok=True)
    return img, lbl


def save_negative(img_path: Path, img_dir: Path, lbl_dir: Path, prefix: str, idx: int) -> None:
    ext = img_path.suffix.lower() or ".jpg"
    name = f"neg_{prefix}_{idx:04d}{ext}"
    shutil.copy2(img_path, img_dir / name)
    (lbl_dir / f"{Path(name).stem}.txt").write_text("", encoding="utf-8")


def import_from_folder(src: Path, img_dir: Path, lbl_dir: Path, max_n: int) -> int:
    files = [p for p in src.rglob("*") if p.is_file() and p.suffix.lower() in IMG_EXTS]
    random.shuffle(files)
    n = 0
    for i, f in enumerate(files[:max_n]):
        save_negative(f, img_dir, lbl_dir, src.name[:8], i)
        n += 1
    return n


def import_from_herb_dataset(base: Path, img_dir: Path, lbl_dir: Path, per_class: int, max_n: int) -> int:
    train = base / "train"
    if not train.exists():
        raise FileNotFoundError(f"未找到: {train}")

    classes = [p for p in train.iterdir() if p.is_dir() and p.name != BAIZHI_NAME]
    random.shuffle(classes)
    n = 0
    idx = 0
    for cls in classes:
        if n >= max_n:
            break
        imgs = [p for p in cls.iterdir() if p.suffix.lower() in IMG_EXTS]
        random.shuffle(imgs)
        for img in imgs[:per_class]:
            if n >= max_n:
                break
            save_negative(img, img_dir, lbl_dir, cls.name[:6], idx)
            idx += 1
            n += 1
    return n


def import_from_camera(camera: int, frames: int, img_dir: Path, lbl_dir: Path) -> int:
    cap = cv2.VideoCapture(camera)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开摄像头 {camera}")
    print(f"采集负样本 {frames} 帧，按 Q 提前结束（画面中不要出现白芷）")
    n = 0
    while n < frames:
        ok, frame = cap.read()
        if not ok:
            break
        show = frame.copy()
        cv2.putText(show, f"NEG {n}/{frames} - press Q to stop", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.imshow("采集负样本", show)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q")):
            break
        name = f"neg_cam_{n:04d}.jpg"
        cv2.imwrite(str(img_dir / name), frame)
        (lbl_dir / f"{Path(name).stem}.txt").write_text("", encoding="utf-8")
        n += 1
    cap.release()
    cv2.destroyAllWindows()
    return n


def main() -> None:
    args = parse_args()
    img_dir, lbl_dir = dst_dirs(args.split)
    total = 0

    if args.camera >= 0:
        total += import_from_camera(args.camera, args.frames, img_dir, lbl_dir)

    if args.source:
        total += import_from_folder(Path(args.source), img_dir, lbl_dir, args.max - total)

    if not args.source and args.camera < 0:
        total += import_from_herb_dataset(
            Path(args.herb_dataset), img_dir, lbl_dir, args.per_class, args.max
        )

    print("=" * 60)
    print(f"负样本导入完成: {total} 张 -> {img_dir}")
    print("标签均为空文件（表示图中无白芷）")
    print("\n请重新训练:")
    print("  python baizhi/scripts/train.py --device 0 --batch 4 --name baizhi_yolov8s_ca_v2")
    print("=" * 60)


if __name__ == "__main__":
    main()
