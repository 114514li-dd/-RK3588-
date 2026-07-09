#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""枸杞单类别 YOLOv8s-CA 训练（流程同白芷 baizhi/scripts/train.py）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baizhi.scripts.train import baizhi_epoch_logger, check_rtx50_gpu_env
from ultralytics import YOLO


def parse_args():
    p = argparse.ArgumentParser(description="Train Gouqi (枸杞) detector")
    p.add_argument("--model", default=str(ROOT / "gouqi/cfg/yolov8s-ca.yaml"))
    p.add_argument("--pretrained", default="yolov8s.pt")
    p.add_argument("--data", default=str(ROOT / "gouqi/dataset/data.yaml"))
    p.add_argument("--epochs", type=int, default=150)
    p.add_argument("--patience", type=int, default=30)
    p.add_argument("--batch", type=int, default=2)
    p.add_argument("--device", default="0")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--name", default="gouqi_yolov8s_ca")
    p.add_argument("--resume", action="store_true")
    return p.parse_args()


def gouqi_epoch_logger(trainer):
    metrics = trainer.metrics or {}
    print(
        f"\n[枸杞 Epoch {trainer.epoch + 1}/{trainer.epochs}] "
        f"Precision={metrics.get('metrics/precision(B)', 0):.4f} | "
        f"Recall={metrics.get('metrics/recall(B)', 0):.4f} | "
        f"mAP@0.5={metrics.get('metrics/mAP50(B)', 0):.4f}"
    )


def main():
    args = parse_args()
    check_rtx50_gpu_env(args.device)
    model = YOLO(args.model)
    model.add_callback("on_fit_epoch_end", gouqi_epoch_logger)
    model.train(
        data=args.data,
        pretrained=args.pretrained,
        epochs=args.epochs,
        patience=args.patience,
        imgsz=640,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=str(ROOT / "gouqi/runs/detect"),
        name=args.name,
        resume=args.resume,
        optimizer="AdamW",
        lr0=0.0008,
        cls=0.3,
        box=7.5,
        mosaic=1.0,
        copy_paste=0.3,
        mixup=0.1,
        close_mosaic=15,
        exist_ok=True,
        verbose=True,
    )
    print(f"\n完成: gouqi/runs/detect/{args.name}/weights/best.pt")


if __name__ == "__main__":
    main()
