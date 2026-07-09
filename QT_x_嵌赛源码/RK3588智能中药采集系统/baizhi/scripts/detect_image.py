#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""白芷检测 — 单张图片推理（YOLOv8 + OpenCV 模块化管线）。

用法:
    python baizhi/scripts/detect_image.py --source path/to/image.jpg
    python baizhi/scripts/detect_image.py --source baizhi/dataset/images/val --conf 0.70
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baizhi.detection import BaizhiDetectConfig, BaizhiDetector, resolve_default_weights


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bai Zhi single-image detection (YOLOv8)")
    parser.add_argument("--weights", type=str, default=resolve_default_weights())
    parser.add_argument("--source", type=str, required=True, help="图片路径或目录")
    parser.add_argument("--conf", type=float, default=0.70)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", type=str, default="")
    parser.add_argument(
        "--save-dir",
        type=str,
        default=str(ROOT / "baizhi/runs/detect/predict_image"),
    )
    parser.add_argument("--box-shrink", type=float, default=0.65)
    parser.add_argument("--json", action="store_true", help="输出 JSON 结果")
    return parser.parse_args()


def collect_sources(source: str) -> list[Path]:
    p = Path(source)
    if p.is_dir():
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        return sorted(f for f in p.iterdir() if f.suffix.lower() in exts)
    return [p]


def main() -> None:
    args = parse_args()
    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    cfg = BaizhiDetectConfig(
        weights=args.weights,
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
        device=args.device,
        box_shrink=args.box_shrink,
    )
    detector = BaizhiDetector(cfg)

    for src in collect_sources(args.source):
        if not src.exists():
            print(f"跳过不存在: {src}")
            continue
        out = save_dir / f"{src.stem}_baizhi{src.suffix or '.jpg'}"
        result = detector.detect_image_and_save(src, out)
        if args.json:
            print(result.to_json())
        else:
            print(
                f"已保存: {out} | 检测数: {result.count} | "
                + ", ".join(f"{b.class_name} {b.confidence:.2f}" for b in result.boxes)
            )


if __name__ == "__main__":
    main()
