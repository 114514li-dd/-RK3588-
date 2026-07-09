#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键提升枸杞置信度：精修标注 + 旋转增强 + 训练 v2。"""

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


def run_script(name: str) -> None:
    path = ROOT / f"gouqi/scripts/{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    mod.main()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--device", default="0")
    p.add_argument("--batch", type=int, default=2)
    p.add_argument("--skip-data", action="store_true")
    args = p.parse_args()

    if not args.skip_data:
        run_script("refine_labels")
        run_script("expand_rotation_train")

    base = ROOT / "gouqi/runs/detect/gouqi_yolov8s_ca/weights/best.pt"
    if not base.exists():
        print("请先运行 启动枸杞训练.bat")
        sys.exit(1)

    check_rtx50_gpu_env(args.device)
    model = YOLO(str(base))
    model.train(
        data=str(ROOT / "gouqi/dataset/data.yaml"),
        epochs=100,
        patience=20,
        imgsz=640,
        batch=args.batch,
        device=args.device,
        workers=2,
        project=str(ROOT / "gouqi/runs/detect"),
        name="gouqi_yolov8s_ca_v2",
        optimizer="AdamW",
        lr0=0.0003,
        cls=0.6,
        box=7.5,
        mosaic=0.9,
        copy_paste=0.4,
        mixup=0.15,
        degrees=90.0,
        fliplr=0.5,
        flipud=0.5,
        hsv_h=0.03,
        hsv_s=0.8,
        hsv_v=0.5,
        translate=0.15,
        scale=0.5,
        close_mosaic=10,
        exist_ok=True,
        verbose=True,
    )
    print("\n完成: gouqi/runs/detect/gouqi_yolov8s_ca_v2/weights/best.pt")
    print("请重新运行 启动白芷枸杞检测.bat")


if __name__ == "__main__":
    main()
