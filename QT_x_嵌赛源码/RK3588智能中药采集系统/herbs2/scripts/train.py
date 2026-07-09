#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""白芷 + 枸杞 双类 YOLOv8s-CA 训练。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baizhi.scripts.train import check_rtx50_gpu_env
from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train Baizhi + Gouqi dual-class detector")
    p.add_argument("--model", default=str(ROOT / "herbs2/cfg/yolov8s-ca.yaml"))
    p.add_argument("--pretrained", default="yolov8s.pt")
    p.add_argument("--data", default=str(ROOT / "herbs2/dataset/data.yaml"))
    p.add_argument("--epochs", type=int, default=150)
    p.add_argument("--patience", type=int, default=30)
    p.add_argument("--batch", type=int, default=2)
    p.add_argument("--device", default="0")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--name", default="herbs2_yolov8s_ca")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--skip-merge", action="store_true", help="跳过 merge_dataset")
    return p.parse_args()


def epoch_logger(trainer) -> None:
    m = trainer.metrics or {}
    print(
        f"\n[双类 Epoch {trainer.epoch + 1}/{trainer.epochs}] "
        f"P={m.get('metrics/precision(B)', 0):.4f} | "
        f"R={m.get('metrics/recall(B)', 0):.4f} | "
        f"mAP@0.5={m.get('metrics/mAP50(B)', 0):.4f}"
    )


def main() -> None:
    args = parse_args()
    if not args.skip_merge:
        import importlib.util

        merge_path = ROOT / "herbs2/scripts/merge_dataset.py"
        spec = importlib.util.spec_from_file_location("merge_dataset", merge_path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        mod.main()

    check_rtx50_gpu_env(args.device)
    model = YOLO(args.model)
    model.add_callback("on_fit_epoch_end", epoch_logger)
    model.train(
        data=args.data,
        pretrained=args.pretrained,
        epochs=args.epochs,
        patience=args.patience,
        imgsz=640,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=str(ROOT / "herbs2/runs/detect"),
        name=args.name,
        resume=args.resume,
        optimizer="AdamW",
        lr0=0.0008,
        cls=0.5,
        box=7.5,
        mosaic=1.0,
        copy_paste=0.3,
        mixup=0.1,
        close_mosaic=15,
        exist_ok=True,
        verbose=True,
    )
    print(f"\n完成: herbs2/runs/detect/{args.name}/weights/best.pt")


if __name__ == "__main__":
    main()
