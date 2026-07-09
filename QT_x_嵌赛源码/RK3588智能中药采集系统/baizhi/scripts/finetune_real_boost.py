#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""白芷实拍过采样 + 微调，提升摄像头置信度（v4/v5 等）。"""

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
        "oversample_real", ROOT / "baizhi/scripts/oversample_real.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def default_base() -> Path:
    for name in (
        "baizhi_yolov8s_ca_v5",
        "baizhi_yolov8s_ca_v4",
        "baizhi_yolov8s_ca_v3",
        "baizhi_yolov8s_ca_v2",
        "baizhi_yolov8s_ca",
    ):
        p = ROOT / f"baizhi/runs/detect/{name}/weights/best.pt"
        if p.exists():
            return p
    return ROOT / "baizhi/runs/detect/baizhi_yolov8s_ca/weights/best.pt"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--device", default="0")
    p.add_argument("--copies", type=int, default=40)
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--batch", type=int, default=4)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--name", default="baizhi_yolov8s_ca_v6")
    p.add_argument("--base", default="", help="微调起点权重，留空则自动选最新 v4/v3")
    p.add_argument("--skip-oversample", action="store_true")
    p.add_argument("--turbo", action="store_true", help="8 epochs, ~3 min")
    p.add_argument("--patience", type=int, default=8)
    p.add_argument("--cls", type=float, default=1.0, help="分类损失权重，略高可抬升 conf")
    args = p.parse_args()

    if args.turbo:
        args.epochs = 8
        args.patience = 3

    if not args.skip_oversample:
        load_oversample().oversample(args.copies)

    base = Path(args.base) if args.base else default_base()
    if not base.exists():
        print("run base baizhi training first")
        sys.exit(1)

    check_rtx50_gpu_env(args.device)
    model = YOLO(str(base))
    model.train(
        data=str(ROOT / "baizhi/dataset/data.yaml"),
        epochs=args.epochs,
        patience=args.patience,
        imgsz=640,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=str(ROOT / "baizhi/runs/detect"),
        name=args.name,
        optimizer="AdamW",
        lr0=0.00015,
        cls=args.cls,
        box=7.5,
        mosaic=0.25,
        copy_paste=0.1,
        mixup=0.0,
        degrees=45.0,
        fliplr=0.5,
        flipud=0.5,
        hsv_h=0.02,
        hsv_s=0.4,
        hsv_v=0.3,
        close_mosaic=3,
        plots=False,
        exist_ok=True,
        verbose=True,
    )
    print(f"\ndone: baizhi/runs/detect/{args.name}/weights/best.pt")


if __name__ == "__main__":
    main()
