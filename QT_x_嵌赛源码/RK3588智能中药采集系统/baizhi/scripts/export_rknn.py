#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""白芷检测模型 RKNN 导出 — 适配瑞芯微 RK3588 INT8 量化部署。

用法（在 PC / WSL / Docker 导出环境中执行，需安装 rknn-toolkit2）:
    python baizhi/scripts/export_rknn.py
    python baizhi/scripts/export_rknn.py --weights baizhi/runs/detect/baizhi_yolov8s_ca/weights/best.pt --int8

RK3588 板端推理请参考 README 中的 rknnlite 部署步骤。
"""

from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Bai Zhi YOLO model to RKNN for RK3588")
    parser.add_argument(
        "--weights",
        type=str,
        default=str(ROOT / "baizhi/runs/detect/baizhi_yolov8s_ca/weights/best.pt"),
    )
    parser.add_argument("--data", type=str, default=str(ROOT / "baizhi/dataset/data.yaml"))
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--name", type=str, default="rk3588", help="目标芯片平台")
    parser.add_argument("--no-int8", action="store_true", help="导出 FP16 模型（默认 INT8）")
    parser.add_argument(
        "--out-dir",
        type=str,
        default=str(ROOT / "baizhi/weights/rknn"),
    )
    parser.add_argument("--onnx-only", action="store_true", help="仅导出 ONNX（Windows 推荐）")
    return parser.parse_args()


def _can_export_rknn() -> bool:
    if platform.system() == "Windows":
        return False
    try:
        import importlib.util

        return importlib.util.find_spec("rknn") is not None
    except ImportError:
        return False


def main() -> None:
    args = parse_args()
    int8 = not args.no_int8
    weights = Path(args.weights)
    if not weights.exists():
        raise FileNotFoundError(f"权重不存在: {weights}\n请先运行 baizhi/scripts/train.py 完成训练")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model = YOLO(str(weights))

    print("=" * 72)
    print("白芷模型 RKNN 导出 | 目标: RK3588")
    print(f"  权重   : {weights}")
    print(f"  量化   : {'INT8' if int8 else 'FP16'}")
    print(f"  imgsz  : {args.imgsz}")
    print("=" * 72)

    # Step 1: 导出 ONNX (opset<=19, RKNN 要求)
    onnx_path = model.export(
        format="onnx",
        imgsz=args.imgsz,
        batch=args.batch,
        simplify=True,
        opset=12,
        dynamic=False,
    )
    print(f"[1/2] ONNX 已导出: {onnx_path}")

    if args.onnx_only or not _can_export_rknn():
        print("\n" + "=" * 72)
        print("ONNX 导出完成。RKNN 转换需在 Linux/WSL2 中执行（Windows 不支持 rknn-toolkit2）")
        print("\nWSL2 中继续执行:")
        print("  pip install rknn-toolkit2>=2.3.2 'onnx<1.19.0' ultralytics")
        print(f"  yolo export model={onnx_path} format=rknn name=rk3588 int8=True data={args.data}")
        print("\n或将以下文件复制到 Linux 机器:")
        print(f"  - {onnx_path}")
        print(f"  - {args.data}")
        print(f"  - {ROOT / 'baizhi/dataset/images'}")
        print("=" * 72)
        return

    # Step 2: ONNX -> RKNN (Linux only)
    rknn_dir = model.export(
        format="rknn",
        imgsz=args.imgsz,
        batch=args.batch,
        name=args.name,
        int8=int8,
        data=args.data,
    )
    print(f"[2/2] RKNN 已导出: {rknn_dir}")
    print("\n部署提示:")
    print("  1. 将 *_rknn_model/ 目录复制到 RK3588 板端")
    print("  2. 板端安装 rknnlite2: pip install rknnlite2")
    print("  3. 使用 baizhi/scripts/rk3588_infer.py 或自研 C++/Python 推理管线")
    print("  4. INT8 量化需保证校准集包含新鲜根/干药材/饮片三种形态")


if __name__ == "__main__":
    main()
