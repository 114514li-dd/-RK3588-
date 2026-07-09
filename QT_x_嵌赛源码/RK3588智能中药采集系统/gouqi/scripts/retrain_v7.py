#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
枸杞 v7 重训练：导入实拍图(多颗标注) -> 过采样 -> 基于 v6 微调 -> 导出 ONNX 到 Qt 项目。

用法（在 ultralytics-main 根目录）:
    C:\\Users\\LWH\\miniconda3\\envs\\baizhi\\python.exe gouqi/scripts/retrain_v7.py --device 0
    C:\\Users\\LWH\\miniconda3\\envs\\baizhi\\python.exe gouqi/scripts/retrain_v7.py --fast --device 0
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baizhi.scripts.train import check_rtx50_gpu_env
from ultralytics import YOLO

QT_ONNX = Path(r"C:\Users\LWH\Desktop\Q\boot\QT1\untitled_1\models\wolfberry_jujube.onnx")
QT_ONNX_RELEASE = Path(
    r"C:\Users\LWH\Desktop\Q\boot\QT1\build-untitled_1-Desktop_Qt_5_15_2_MSVC2019_64bit-Release\release\models\wolfberry_jujube.onnx"
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def default_base() -> Path:
    for name in (
        "gouqi_yolov8s_ca_v6",
        "gouqi_yolov8s_ca_v5",
        "gouqi_yolov8s_ca_v4",
        "gouqi_yolov8s_ca",
    ):
        p = ROOT / f"gouqi/runs/detect/{name}/weights/best.pt"
        if p.exists():
            return p
    return ROOT / "gouqi/runs/detect/gouqi_yolov8s_ca/weights/best.pt"


def export_onnx(pt_path: Path) -> Path:
    model = YOLO(str(pt_path))
    out = model.export(
        format="onnx",
        imgsz=640,
        opset=11,
        simplify=False,
        dynamic=False,
        half=False,
        nms=False,
    )
    return Path(out)


def deploy_onnx(onnx_path: Path) -> None:
    QT_ONNX.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(onnx_path, QT_ONNX)
    print(f"ONNX -> {QT_ONNX}")
    if QT_ONNX_RELEASE.parent.is_dir():
        shutil.copy2(onnx_path, QT_ONNX_RELEASE)
        print(f"ONNX -> {QT_ONNX_RELEASE}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--device", default="0")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--patience", type=int, default=12)
    p.add_argument("--batch", type=int, default=4)
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--copies", type=int, default=35, help="实拍过采样份数")
    p.add_argument("--name", default="gouqi_yolov8s_ca_v7")
    p.add_argument("--skip-import", action="store_true")
    p.add_argument("--skip-oversample", action="store_true")
    p.add_argument("--skip-export", action="store_true")
    p.add_argument("--fast", action="store_true", help="快速试训 20 轮")
    args = p.parse_args()

    if args.fast:
        args.epochs = 20
        args.patience = 6
        args.copies = 20

    if not args.skip_import:
        imp = load_module("import_user_images", ROOT / "gouqi/scripts/import_user_images.py")
        sources = imp.discover_user_images()
        if not sources:
            print("未找到实拍图，跳过导入")
        else:
            n = imp.import_images(sources, prefix="real")
            print(f"实拍导入 {n} 张")

    if not args.skip_oversample:
        n = load_module("oversample_real", ROOT / "gouqi/scripts/oversample_real.py").oversample(
            args.copies
        )
        print(f"实拍过采样 {n} 张")

    base = default_base()
    if not base.exists():
        print("缺少基础权重，请先运行 gouqi/scripts/train.py")
        sys.exit(1)

    print(f"微调基座: {base}")
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
        lr0=0.00012,
        cls=0.8,
        box=7.5,
        mosaic=0.35,
        copy_paste=0.15,
        mixup=0.05,
        degrees=45.0,
        fliplr=0.5,
        flipud=0.5,
        hsv_h=0.02,
        hsv_s=0.55,
        hsv_v=0.35,
        close_mosaic=6,
        exist_ok=True,
        verbose=True,
    )

    best = ROOT / f"gouqi/runs/detect/{args.name}/weights/best.pt"
    print(f"\n训练完成: {best}")

    if not args.skip_export and best.exists():
        onnx_path = export_onnx(best)
        deploy_onnx(onnx_path)
        print("请重新运行 Qt 程序测试 AI 识别")


if __name__ == "__main__":
    main()
