#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导入实拍图 + 微调枸杞模型（v4/v5）。"""

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
    ASSETS / "c__Users_LWH_AppData_Roaming_Cursor_User_workspaceStorage_0a8ee5a6fac4e88e451f9f810ba6147c_images_ab967bbc0a2b87f9c365183b7d46c1b1-586e8e4f-92f5-4c4b-992d-832cafb639fa.png",
    ASSETS / "c__Users_LWH_AppData_Roaming_Cursor_User_workspaceStorage_0a8ee5a6fac4e88e451f9f810ba6147c_images_e6e453060680eb872c406e4e1951a962-ffca9a3a-5f5b-4cf0-b244-b1ab4fd83b96.png",
    ASSETS / "c__Users_LWH_AppData_Roaming_Cursor_User_workspaceStorage_0a8ee5a6fac4e88e451f9f810ba6147c_images_5ed13f8eb407f4c8d9cf175718f9d3b6-55affbb9-d5b1-4b17-bbd4-392969c6d9d1.png",
    ASSETS / "c__Users_LWH_AppData_Roaming_Cursor_User_workspaceStorage_0a8ee5a6fac4e88e451f9f810ba6147c_images_9f477279e7980b3bdcd1c568613f9ea4-53ca64db-095d-4eac-b73f-4961f5f11e2c.png",
    ASSETS / "c__Users_LWH_AppData_Roaming_Cursor_User_workspaceStorage_0a8ee5a6fac4e88e451f9f810ba6147c_images_daf842cd7a5e20e9f6b599085347abef-8e40190e-3f4e-42cc-8fca-af0fa2b2696a.png",
]


def run_import(images: list[Path]) -> None:
    spec = importlib.util.spec_from_file_location(
        "import_user_images", ROOT / "gouqi/scripts/import_user_images.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    mod.import_images(images, prefix="real")


def default_base() -> Path:
    for name in ("gouqi_yolov8s_ca_v4", "gouqi_yolov8s_ca_v3", "gouqi_yolov8s_ca_v2", "gouqi_yolov8s_ca"):
        p = ROOT / f"gouqi/runs/detect/{name}/weights/best.pt"
        if p.exists():
            return p
    return ROOT / "gouqi/runs/detect/gouqi_yolov8s_ca/weights/best.pt"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--device", default="0")
    p.add_argument("--batch", type=int, default=1)
    p.add_argument("--workers", type=int, default=0, help="0 可避免 Windows 内存溢出")
    p.add_argument("--epochs", type=int, default=60)
    p.add_argument("--patience", type=int, default=15)
    p.add_argument("--name", default="gouqi_yolov8s_ca_v5")
    p.add_argument("--skip-import", action="store_true")
    p.add_argument("--resume", action="store_true", help="从同名 run 的 last.pt 继续")
    p.add_argument(
        "--fast",
        action="store_true",
        help="快速微调：20轮、batch=2、轻增强，约 10~15 分钟",
    )
    args = p.parse_args()

    if args.fast:
        args.epochs = 20
        args.patience = 5
        args.batch = max(args.batch, 2)
        args.resume = False

    if not args.skip_import:
        imgs = [p for p in USER_IMAGES if p.exists()]
        if imgs:
            run_import(imgs)
        else:
            print("未找到用户实拍图，仅基于现有数据集训练")

    run_dir = ROOT / "gouqi/runs/detect" / args.name
    best_pt = run_dir / "weights/best.pt"
    last_pt = run_dir / "weights/last.pt"
    if args.resume and last_pt.exists():
        base = last_pt
    elif args.fast and best_pt.exists():
        base = best_pt
    else:
        base = default_base()
    if not base.exists():
        print("请先完成基础枸杞训练")
        sys.exit(1)

    mosaic = 0.3 if args.fast else 0.5
    copy_paste = 0.1 if args.fast else 0.3
    mixup = 0.0 if args.fast else 0.1

    check_rtx50_gpu_env(args.device)
    model = YOLO(str(base))
    model.train(
        data=str(ROOT / "gouqi/dataset/data.yaml"),
        epochs=args.epochs,
        patience=args.patience,
        imgsz=640,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=str(ROOT / "gouqi/runs/detect"),
        name=args.name,
        optimizer="AdamW",
        lr0=0.0002,
        cls=0.6,
        box=7.5,
        mosaic=mosaic,
        copy_paste=copy_paste,
        mixup=mixup,
        degrees=90.0,
        fliplr=0.5,
        flipud=0.5,
        hsv_h=0.03,
        hsv_s=0.7,
        hsv_v=0.4,
        close_mosaic=5 if args.fast else 8,
        exist_ok=True,
        resume=args.resume and last_pt.exists(),
        verbose=True,
    )
    print(f"\n完成: gouqi/runs/detect/{args.name}/weights/best.pt")


if __name__ == "__main__":
    main()
