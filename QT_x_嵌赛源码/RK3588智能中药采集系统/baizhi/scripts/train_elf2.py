#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ELF2 精确识别训练 — 针对端侧部署优化，降低误检。

参考飞凌 ELF2 AI 端侧部署案例要点:
  1. 负样本 >= 正样本 2 倍
  2. 三种形态均衡 + 易混淆药材
  3. 训练后导出 RKNN INT8 在板端验证

用法:
    conda activate baizhi
    python baizhi/scripts/train_elf2.py --device 0 --batch 2
"""

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
    p = argparse.ArgumentParser(description="Train Bai Zhi for ELF2 precision deployment")
    p.add_argument("--model", type=str, default=str(ROOT / "baizhi/cfg/yolov8s-ca.yaml"))
    p.add_argument("--pretrained", type=str, default="yolov8s.pt")
    p.add_argument("--data", type=str, default=str(ROOT / "baizhi/dataset/data.yaml"))
    p.add_argument("--epochs", type=int, default=150)
    p.add_argument("--patience", type=int, default=30)
    p.add_argument("--batch", type=int, default=2)
    p.add_argument("--device", type=str, default="0")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--name", type=str, default="baizhi_elf2")
    p.add_argument("--resume", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    check_rtx50_gpu_env(args.device)

    model = YOLO(args.model)
    model.add_callback("on_fit_epoch_end", baizhi_epoch_logger)

    print("=" * 72)
    print("ELF2 白芷精确识别训练")
    print("  目标: 降低误检 + RK3588 INT8 部署")
    print("  建议: 负样本>=2x正样本, 含场景/易混淆药材")
    print("=" * 72)

    model.train(
        data=args.data,
        pretrained=args.pretrained,
        epochs=args.epochs,
        patience=args.patience,
        imgsz=640,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=str(ROOT / "baizhi/runs/detect"),
        name=args.name,
        resume=args.resume,
        optimizer="AdamW",
        lr0=0.0006,
        lrf=0.01,
        box=7.5,
        cls=0.5,
        dfl=1.5,
        mosaic=0.8,
        copy_paste=0.2,
        mixup=0.05,
        close_mosaic=20,
        amp=True,
        seed=42,
        val=True,
        plots=True,
        save=True,
        exist_ok=True,
        verbose=True,
    )

    best = ROOT / "baizhi/runs/detect" / args.name / "weights" / "best.pt"
    print(f"\n训练完成: {best}")
    print("导出 ELF2: python baizhi/scripts/export_elf2.py --weights", best)


if __name__ == "__main__":
    main()
