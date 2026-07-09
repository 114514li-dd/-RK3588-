#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""白芷单类别 YOLOv8s-CA 训练脚本。

用法（在项目根目录 ultralytics-main 下执行）:
    python baizhi/scripts/train.py
    python baizhi/scripts/train.py --epochs 200 --device 0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def check_rtx50_gpu_env(device: str) -> None:
    """RTX 50 系 (sm_120) 需 baizhi 环境：torch 2.7+ cu128。"""
    import torch

    use_cuda = device not in {"", "cpu"} or (not device and torch.cuda.is_available())
    if not use_cuda or not torch.cuda.is_available():
        return

    cap = torch.cuda.get_device_capability()
    arch = torch.cuda.get_arch_list()
    if cap >= (12, 0) and "sm_120" not in arch:
        print("\n" + "=" * 72)
        print("错误: 当前 PyTorch 不支持 RTX 5060 (sm_120)")
        print(f"  Python : {sys.executable}")
        print(f"  PyTorch: {torch.__version__}")
        print(f"  支持架构: {arch}")
        print("\n请改用 baizhi 环境训练:")
        print("  conda activate baizhi")
        print("  python baizhi/scripts/train.py --device 0 --batch 16")
        print("\n或直接双击: baizhi/scripts/train_gpu.bat")
        print("=" * 72 + "\n")
        sys.exit(1)


from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Bai Zhi (白芷) detector with YOLOv8s-CA")
    parser.add_argument("--model", type=str, default=str(ROOT / "baizhi/cfg/yolov8s-ca.yaml"))
    parser.add_argument("--pretrained", type=str, default="yolov8s.pt", help="预训练权重")
    parser.add_argument("--data", type=str, default=str(ROOT / "baizhi/dataset/data.yaml"))
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--patience", type=int, default=40)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=4, help="RTX 5060 8GB 建议 4~8")
    parser.add_argument("--device", type=str, default="", help="cuda:0 / cpu / 留空自动")
    parser.add_argument("--workers", type=int, default=4, help="降低 workers 可节省内存")
    parser.add_argument("--project", type=str, default=str(ROOT / "baizhi/runs/detect"))
    parser.add_argument("--name", type=str, default="baizhi_yolov8s_ca")
    parser.add_argument("--resume", action="store_true", help="从上次 checkpoint 恢复")
    return parser.parse_args()


def baizhi_epoch_logger(trainer) -> None:
    """每轮打印白芷类别 Precision / Recall / mAP@0.5。"""
    metrics = trainer.metrics or {}
    precision = metrics.get("metrics/precision(B)", 0.0)
    recall = metrics.get("metrics/recall(B)", 0.0)
    map50 = metrics.get("metrics/mAP50(B)", 0.0)
    map5095 = metrics.get("metrics/mAP50-95(B)", 0.0)
    box_loss = float(trainer.tloss[0]) if trainer.tloss is not None and len(trainer.tloss) > 0 else 0.0
    cls_loss = float(trainer.tloss[1]) if trainer.tloss is not None and len(trainer.tloss) > 1 else 0.0
    dfl_loss = float(trainer.tloss[2]) if trainer.tloss is not None and len(trainer.tloss) > 2 else 0.0
    lr = trainer.optimizer.param_groups[0]["lr"] if trainer.optimizer else 0.0

    print(
        f"\n[白芷 Epoch {trainer.epoch + 1}/{trainer.epochs}] "
        f"Precision={precision:.4f} | Recall={recall:.4f} | mAP@0.5={map50:.4f} | mAP@0.5:0.95={map5095:.4f} | "
        f"box={box_loss:.4f} cls={cls_loss:.4f} dfl={dfl_loss:.4f} | lr={lr:.6f}"
    )


def main() -> None:
    args = parse_args()
    check_rtx50_gpu_env(args.device)

    # 加载 C2fCA 结构，train() 中通过 pretrained 迁移 yolov8s 骨干权重
    model = YOLO(args.model)
    model.add_callback("on_fit_epoch_end", baizhi_epoch_logger)

    train_kwargs = dict(
        data=args.data,
        pretrained=args.pretrained,
        epochs=args.epochs,
        patience=args.patience,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=args.project,
        name=args.name,
        resume=args.resume,
        # 优化器与学习率
        optimizer="AdamW",
        lr0=0.0008,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3.0,
        # 损失权重：单类检测降低 cls 增益，强化定位
        box=7.5,
        cls=0.3,
        dfl=1.5,
        # 细长物体 & 堆叠遮挡增强
        mosaic=1.0,
        copy_paste=0.3,
        copy_paste_mode="flip",
        mixup=0.1,
        close_mosaic=15,
        # 其他
        amp=True,
        cache=False,
        seed=42,
        val=True,
        plots=True,
        save=True,
        save_period=10,
        exist_ok=True,
        verbose=True,
    )

    print("=" * 72)
    print("白芷单类别检测训练 | YOLOv8s + C2fCA | 目标平台: RK3588")
    print(f"  模型结构 : {args.model}")
    print(f"  预训练   : {args.pretrained}")
    print(f"  数据集   : {args.data}")
    print(f"  imgsz={args.imgsz} | epochs={args.epochs} | patience={args.patience}")
    print(f"  增强     : mosaic=1.0, copy_paste=0.3, mixup=0.1")
    print(f"  优化器   : AdamW, lr0=0.0008, cls=0.3")
    print("=" * 72)

    results = model.train(**train_kwargs)
    best = Path(results.save_dir) / "weights" / "best.pt"
    print(f"\n训练完成，最佳权重: {best}")
    print("下一步: python baizhi/scripts/export_rknn.py --weights", best)


if __name__ == "__main__":
    main()
