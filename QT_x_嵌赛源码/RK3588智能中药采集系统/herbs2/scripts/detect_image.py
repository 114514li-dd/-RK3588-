#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双类模型单张图片测试（排查摄像头检不出时用）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ultralytics import YOLO

CLASS_CN = {0: "白芷", 1: "枸杞"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("image", help="图片路径")
    p.add_argument("--weights", default=str(ROOT / "herbs2/runs/detect/herbs2_yolov8s_ca/weights/best.pt"))
    p.add_argument("--conf", type=float, default=0.20)
    p.add_argument("--device", default="0")
    args = p.parse_args()

    model = YOLO(args.weights)
    r = model.predict(args.image, conf=args.conf, device=args.device, save=True, verbose=False)[0]
    boxes = r.boxes
    if boxes is None or len(boxes) == 0:
        print(f"未检出 (conf>={args.conf})，可试 --conf 0.10")
        return
    for b in boxes:
        cid = int(b.cls)
        print(f"{CLASS_CN.get(cid, cid)} conf={float(b.conf):.3f}")
    print(f"结果已保存到 runs/detect/predict/")


if __name__ == "__main__":
    main()
