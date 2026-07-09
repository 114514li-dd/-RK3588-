#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""白芷检测 CLI — 供 Qt / 外部程序调用，输出结构化 JSON。

用法:
    python baizhi/scripts/baizhi_detect_cli.py image.jpg
    python baizhi/scripts/baizhi_detect_cli.py image.jpg --save result.jpg
    python baizhi/scripts/baizhi_detect_cli.py image.jpg --conf 0.70 --device 0
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
    p = argparse.ArgumentParser(description="Baizhi YOLOv8 detect CLI (JSON output)")
    p.add_argument("source", type=str, help="图片路径")
    p.add_argument("--weights", type=str, default=resolve_default_weights())
    p.add_argument("--conf", type=float, default=0.55)
    p.add_argument("--iou", type=float, default=0.45)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--device", type=str, default="")
    p.add_argument("--save", type=str, default="", help="可选：保存带框图片路径")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = BaizhiDetectConfig(
        weights=args.weights,
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
        device=args.device,
    )
    detector = BaizhiDetector(cfg)

    if args.save:
        result = detector.detect_image_and_save(args.source, args.save)
    else:
        result = detector.detect_image(args.source)

    print(result.to_json())
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
