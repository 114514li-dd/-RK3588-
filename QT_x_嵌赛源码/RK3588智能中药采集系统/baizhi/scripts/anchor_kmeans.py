#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""白芷数据集 K-means 框形聚类 — 分析细长目标宽高比，生成训练先验建议。

说明:
    YOLOv8 为 anchor-free 架构，不使用传统 anchor box。
    本脚本对标注框做 K-means 聚类，输出:
      1) 目标宽高比分布与推荐 imgsz / 增强参数
      2) shape_priors.yaml 供训练调参参考
      3) 若需 YOLOv5 等 anchor-based 模型，可据此替换 anchors

用法:
    python baizhi/scripts/anchor_kmeans.py
    python baizhi/scripts/anchor_kmeans.py --data baizhi/dataset/data.yaml --k 9 --imgsz 640
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="K-means clustering for Bai Zhi bbox shapes")
    parser.add_argument("--data", type=str, default=str(ROOT / "baizhi/dataset/data.yaml"))
    parser.add_argument("--split", type=str, default="train", choices=["train", "val", "both"])
    parser.add_argument("--k", type=int, default=9, help="聚类数（YOLOv5 常用 9，YOLOv8 作参考）")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--iters", type=int, default=300)
    parser.add_argument(
        "--out",
        type=str,
        default=str(ROOT / "baizhi/cfg/shape_priors.yaml"),
    )
    return parser.parse_args()


def load_data_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    base = path.parent
    if not Path(data["path"]).is_absolute():
        data["root"] = (ROOT / data["path"]).resolve() if not (base / data["path"]).exists() else (base / "..").resolve()
        root_candidate = ROOT / data["path"]
        data["root"] = root_candidate.resolve() if root_candidate.exists() else (ROOT / "baizhi/dataset").resolve()
    else:
        data["root"] = Path(data["path"]).resolve()
    return data


def collect_boxes(label_dirs: list[Path], img_dirs: list[Path]) -> np.ndarray:
    """返回 Nx2 数组: [width_px, height_px]。"""
    wh_list = []
    for label_dir, img_dir in zip(label_dirs, img_dirs):
        if not label_dir.exists():
            print(f"警告: 标注目录不存在 {label_dir}")
            continue
        for label_path in label_dir.glob("*.txt"):
            img_stem = label_path.stem
            img_path = None
            for ext in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
                p = img_dir / f"{img_stem}{ext}"
                if p.exists():
                    img_path = p
                    break
            if img_path is None:
                continue
            try:
                import cv2

                im = cv2.imread(str(img_path))
                if im is None:
                    continue
                h, w = im.shape[:2]
            except ImportError:
                from PIL import Image

                with Image.open(img_path) as im:
                    w, h = im.size

            lines = label_path.read_text(encoding="utf-8").strip().splitlines()
            for line in lines:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                _, bw, bh, _, _ = map(float, parts[:5])
                wh_list.append([bw * w, bh * h])
    return np.array(wh_list, dtype=np.float64)


def kmeans_wh(data: np.ndarray, k: int, iters: int) -> tuple[np.ndarray, np.ndarray]:
    """K-means on (w, h), return centers (k,2) and labels."""
    if len(data) < k:
        raise ValueError(f"样本数 {len(data)} 少于聚类数 k={k}，请先补充标注数据")
    rng = np.random.default_rng(42)
    centers = data[rng.choice(len(data), k, replace=False)]
    for _ in range(iters):
        dist = np.linalg.norm(data[:, None, :] - centers[None, :, :], axis=2)
        labels = dist.argmin(axis=1)
        new_centers = np.array([data[labels == i].mean(axis=0) if (labels == i).any() else centers[i] for i in range(k)])
        if np.allclose(new_centers, centers):
            break
        centers = new_centers
    order = np.argsort(centers[:, 0] * centers[:, 1])
    return centers[order], labels


def main() -> None:
    args = parse_args()
    cfg = load_data_yaml(Path(args.data))
    root = Path(cfg["root"])

    splits = ["train", "val"] if args.split == "both" else [args.split]
    label_dirs = [root / "labels" / s for s in splits]
    img_dirs = [root / "images" / s for s in splits]

    wh = collect_boxes(label_dirs, img_dirs)
    if len(wh) == 0:
        print("未找到任何标注框。请先将图片放入 dataset/images/train 并编写同名 .txt 标注。")
        print("示例标注 (整根白芷): 0 0.512 0.498 0.085 0.620")
        sys.exit(1)

    centers, _ = kmeans_wh(wh, args.k, args.iters)
    ratios = wh[:, 0] / np.maximum(wh[:, 1], 1e-6)
    median_ratio = float(np.median(ratios))
    elongated = median_ratio < 0.7 or median_ratio > 1.4

    # 归一化到 imgsz 网格的 anchor 参考（供 YOLOv5 或分析用）
    scale = args.imgsz / max(np.sqrt((wh[:, 0] * wh[:, 1]).mean()), 1.0)
    anchors_norm = (centers * scale / args.imgsz).tolist()
    anchors_pixel = centers.tolist()

    report = {
        "note": "YOLOv8 为 anchor-free；本文件仅供形状先验分析与 YOLOv5 迁移参考",
        "num_boxes": int(len(wh)),
        "imgsz": args.imgsz,
        "median_aspect_ratio_w_over_h": round(median_ratio, 4),
        "is_predominantly_elongated": elongated,
        "mean_width_px": round(float(wh[:, 0].mean()), 2),
        "mean_height_px": round(float(wh[:, 1].mean()), 2),
        "kmeans_centers_wh_pixel": anchors_pixel,
        "kmeans_centers_wh_normalized": anchors_norm,
        "training_recommendations": {
            "mosaic": 1.0,
            "copy_paste": 0.3,
            "mixup": 0.1,
            "close_mosaic": 15,
            "rect_training": elongated,
            "cls_gain": 0.3,
            "comment": "白芷根细长、饮片近圆，建议三种形态混合标注并开启 copy_paste 缓解堆叠遮挡",
        },
        # YOLOv5 格式 anchors (w,h 相对 grid)，三尺度各 3 个
        "yolov5_style_anchors_wh": [
            [round(c[0] / args.imgsz, 4), round(c[1] / args.imgsz, 4)] for c in centers[:3]
        ]
        + [[round(c[0] / args.imgsz, 4), round(c[1] / args.imgsz, 4)] for c in centers[3:6]]
        + [[round(c[0] / args.imgsz, 4), round(c[1] / args.imgsz, 4)] for c in centers[6:9]],
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(report, f, allow_unicode=True, sort_keys=False)

    json_path = out_path.with_suffix(".json")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 60)
    print("白芷目标框 K-means 聚类完成")
    print(f"  样本框数     : {len(wh)}")
    print(f"  中位宽高比   : {median_ratio:.3f} ({'细长' if elongated else '近方形'})")
    print(f"  聚类中心(px) :")
    for i, (w, h) in enumerate(anchors_pixel):
        print(f"    [{i}] w={w:.1f}, h={h:.1f}, ratio={w/h:.3f}")
    print(f"  输出         : {out_path}")
    print(f"  JSON         : {json_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
