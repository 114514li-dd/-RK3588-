#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""白芷检测 — 摄像头实时推理（YOLOv8 + OpenCV 模块化管线）。

用法:
    python baizhi/scripts/detect_camera.py --mode balanced
    python baizhi/scripts/detect_camera.py --mode strict --conf 0.75
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check_rtx50_gpu_env(device: str) -> None:
    """RTX 5060 需 baizhi 环境 (torch 2.7+cu128)，否则报 no kernel image。"""
    import torch

    use_cuda = device not in {"", "cpu"} or (not device and torch.cuda.is_available())
    if not use_cuda or not torch.cuda.is_available():
        return
    cap = torch.cuda.get_device_capability()
    arch = torch.cuda.get_arch_list()
    if cap >= (12, 0) and "sm_120" not in arch:
        print("\n" + "=" * 72)
        print("错误: 当前 Python 不支持 RTX 5060 GPU 推理")
        print(f"  Python : {sys.executable}")
        print(f"  PyTorch: {torch.__version__}")
        print("\n请改用 baizhi 环境:")
        print("  conda activate baizhi")
        print("  python baizhi/scripts/detect_camera.py --device 0")
        print("\n或双击: baizhi/scripts/detect_camera_gpu.bat")
        print("=" * 72 + "\n")
        sys.exit(1)


from baizhi.detection import BaizhiDetectConfig, BaizhiDetector, resolve_default_weights, run_camera_loop


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bai Zhi realtime camera detection (YOLOv8)")
    parser.add_argument("--weights", type=str, default=resolve_default_weights())
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument(
        "--mode",
        type=str,
        default="balanced",
        choices=["balanced", "strict"],
        help="balanced=优先检出; strict=优先减少误检",
    )
    parser.add_argument("--conf", type=float, default=None)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", type=str, default="")
    parser.add_argument("--min-area", type=float, default=None)
    parser.add_argument("--max-area", type=float, default=None)
    parser.add_argument("--confirm", type=int, default=None)
    parser.add_argument("--max-det", type=int, default=5)
    parser.add_argument("--max-fps", type=float, default=10.0)
    parser.add_argument("--infer-every", type=int, default=2)
    parser.add_argument("--cam-width", type=int, default=640)
    parser.add_argument("--cam-height", type=int, default=480)
    parser.add_argument("--hold-ms", type=int, default=0)
    parser.add_argument("--box-shrink", type=float, default=0.65)
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> BaizhiDetectConfig:
    base = BaizhiDetectConfig.balanced() if args.mode == "balanced" else BaizhiDetectConfig.strict()
    base.weights = args.weights
    base.iou = args.iou
    base.imgsz = args.imgsz
    base.device = args.device
    base.max_det = args.max_det
    base.max_fps = args.max_fps
    base.infer_every = args.infer_every
    base.hold_ms = args.hold_ms
    base.box_shrink = args.box_shrink
    if args.conf is not None:
        base.conf = args.conf
    if args.min_area is not None:
        base.min_area_ratio = args.min_area
    if args.max_area is not None:
        base.max_area_ratio = args.max_area
    if args.confirm is not None:
        base.confirm_frames = args.confirm
    return base


def main() -> None:
    args = parse_args()
    cfg = build_config(args)
    check_rtx50_gpu_env(cfg.device)

    print(f"模式={args.mode} | conf>={cfg.conf} | confirm={cfg.confirm_frames} | max_fps={cfg.max_fps}")
    print(f"权重: {cfg.weights}")
    print("误检多时用 --mode strict；检不出时用 --conf 0.40 或 --confirm 1")
    print("按 Q 退出")

    detector = BaizhiDetector(cfg)
    run_camera_loop(
        detector,
        camera_index=args.camera,
        width=args.cam_width,
        height=args.cam_height,
    )


if __name__ == "__main__":
    main()
