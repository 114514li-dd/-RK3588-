#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导入白芷实拍图 + 微调模型（v3）。"""

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

ASSETS = Path(
    r"C:\Users\LWH\.cursor\projects\c-Users-LWH-Desktop-ultralytics-main\assets"
)
USER_IMAGES = [
    ASSETS / "c__Users_LWH_AppData_Roaming_Cursor_User_workspaceStorage_0a8ee5a6fac4e88e451f9f810ba6147c_images_ab6ad57e866fde45b58ac28f6ef8f3b2-d993530d-5018-40e0-b342-bcaafa075953.png",
    ASSETS / "c__Users_LWH_AppData_Roaming_Cursor_User_workspaceStorage_0a8ee5a6fac4e88e451f9f810ba6147c_images_2956b620f64f5cac4a9e886ce476bf51-344ca21e-305b-4201-a334-eb3c0b42fcee.png",
    ASSETS / "c__Users_LWH_AppData_Roaming_Cursor_User_workspaceStorage_0a8ee5a6fac4e88e451f9f810ba6147c_images_8f38afeff47877b7d5c47c5d12fe417c-b97b927d-8f8b-44e3-915c-92451aee5082.png",
    ASSETS / "c__Users_LWH_AppData_Roaming_Cursor_User_workspaceStorage_0a8ee5a6fac4e88e451f9f810ba6147c_images_01e4bf1d1ff40af9bc13c7e4a6f0bab2-996aa5b2-53ed-47c9-ab66-6474cb0c2e9f.png",
]


def run_import(images: list[Path]) -> None:
    spec = importlib.util.spec_from_file_location(
        "import_user_images", ROOT / "baizhi/scripts/import_user_images.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    mod.import_images(images, prefix="real")


def default_base() -> Path:
    for name in ("baizhi_yolov8s_ca_v2", "baizhi_yolov8s_ca"):
        p = ROOT / f"baizhi/runs/detect/{name}/weights/best.pt"
        if p.exists():
            return p
    return ROOT / "baizhi/runs/detect/baizhi_yolov8s_ca/weights/best.pt"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--device", default="0")
    p.add_argument("--batch", type=int, default=2)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--patience", type=int, default=10)
    p.add_argument("--name", default="baizhi_yolov8s_ca_v3")
    p.add_argument("--skip-import", action="store_true")
    p.add_argument("--fast", action="store_true", help="10 epochs, ~4 min")
    p.add_argument("--turbo", action="store_true", help="6 epochs imgsz512, ~2 min")
    args = p.parse_args()

    imgsz = 640
    mosaic, copy_paste, mixup = 0.4, 0.15, 0.05
    plots = True

    if args.turbo:
        args.epochs = 6
        args.patience = 3
        args.batch = max(args.batch, 4)
        imgsz = 512
        mosaic, copy_paste, mixup = 0.15, 0.0, 0.0
        plots = False
    elif args.fast:
        args.epochs = 10
        args.patience = 4
        mosaic, copy_paste, mixup = 0.25, 0.1, 0.0
        plots = False

    if not args.skip_import:
        imgs = [x for x in USER_IMAGES if x.exists()]
        if imgs:
            run_import(imgs)
        else:
            print("no user images found, train on existing dataset only")

    base = default_base()
    if not base.exists():
        print("run base baizhi training first")
        sys.exit(1)

    check_rtx50_gpu_env(args.device)
    model = YOLO(str(base))
    model.train(
        data=str(ROOT / "baizhi/dataset/data.yaml"),
        epochs=args.epochs,
        patience=args.patience,
        imgsz=imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=str(ROOT / "baizhi/runs/detect"),
        name=args.name,
        optimizer="AdamW",
        lr0=0.0002 if args.turbo else 0.00015,
        cls=0.4,
        box=7.5,
        mosaic=mosaic,
        copy_paste=copy_paste,
        mixup=mixup,
        degrees=30.0 if args.turbo else 45.0,
        fliplr=0.5,
        flipud=0.5,
        close_mosaic=3 if args.turbo else 5,
        plots=plots,
        exist_ok=True,
        verbose=True,
    )
    print(f"\ndone: baizhi/runs/detect/{args.name}/weights/best.pt")


if __name__ == "__main__":
    main()
