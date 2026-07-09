#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实拍图过采样 + 微调 v6，提升摄像头置信度。"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baizhi.scripts.train import check_rtx50_gpu_env
from ultralytics import YOLO


def load_oversample():
    spec = importlib.util.spec_from_file_location(
        "oversample_real", ROOT / "gouqi/scripts/oversample_real.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def default_base() -> Path:
    for name in ("gouqi_yolov8s_ca_v5", "gouqi_yolov8s_ca_v4", "gouqi_yolov8s_ca_v3", "gouqi_yolov8s_ca"):
        p = ROOT / f"gouqi/runs/detect/{name}/weights/best.pt"
        if p.exists():
            return p
    return ROOT / "gouqi/runs/detect/gouqi_yolov8s_ca/weights/best.pt"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--device", default="0")
    p.add_argument("--copies", type=int, default=40)
    p.add_argument("--epochs", type=int, default=25)
    p.add_argument("--batch", type=int, default=2)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--name", default="gouqi_yolov8s_ca_v6")
    p.add_argument("--skip-oversample", action="store_true")
    args = p.parse_args()

    if not args.skip_oversample:
        load_oversample().oversample(args.copies)

    base = default_base()
    if not base.exists():
        print("请先完成枸杞基础训练")
        sys.exit(1)

    check_rtx50_gpu_env(args.device)
    model = YOLO(str(base))
    model.train(
        data=str(ROOT / "gouqi/dataset/data.yaml"),
        epochs=args.epochs,
        patience=8,
        imgsz=640,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=str(ROOT / "gouqi/runs/detect"),
        name=args.name,
        optimizer="AdamW",
        lr0=0.00015,
        cls=0.6,
        box=7.5,
        mosaic=0.3,
        copy_paste=0.1,
        mixup=0.0,
        degrees=45.0,
        fliplr=0.5,
        flipud=0.5,
        hsv_h=0.02,
        hsv_s=0.5,
        hsv_v=0.3,
        close_mosaic=5,
        exist_ok=True,
        verbose=True,
    )
    print(f"\n完成: gouqi/runs/detect/{args.name}/weights/best.pt")


if __name__ == "__main__":
    main()
