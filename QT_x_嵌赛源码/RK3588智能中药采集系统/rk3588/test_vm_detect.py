#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ubuntu 虚拟机 / PC Linux：用 PyTorch 权重验证枸杞、白芷识别（无需 RKNN）。

用法:
  # 摄像头（VMware 需 USB 摄像头 passthrough）
  python3 rk3588/test_vm_detect.py --herb both --camera 0

  # 单张图片
  python3 rk3588/test_vm_detect.py --herb gouqi --source /path/to/test.jpg --save out.jpg

  # CPU（虚拟机无 GPU）
  python3 rk3588/test_vm_detect.py --herb both --camera 0 --device cpu
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ultralytics import YOLO


def pick_weight(*candidates: Path) -> Path:
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError("未找到权重: " + ", ".join(str(c) for c in candidates))


def resolve_weights(herb: str) -> dict[str, Path]:
    w = {}
    if herb in ("gouqi", "both"):
        w["gouqi"] = pick_weight(
            ROOT / "gouqi/runs/detect/gouqi_yolov8s_ca_v8/weights/best.pt",
            ROOT / "gouqi/runs/detect/gouqi_yolov8s_ca_v7/weights/best.pt",
            ROOT / "gouqi/runs/detect/gouqi_yolov8s_ca_v6/weights/best.pt",
        )
    if herb in ("baizhi", "both"):
        w["baizhi"] = pick_weight(
            ROOT / "baizhi/runs/detect/baizhi_yolov8s_ca_v7/weights/best.pt",
            ROOT / "baizhi/runs/detect/baizhi_yolov8s_ca_v6/weights/best.pt",
            ROOT / "baizhi/runs/detect/baizhi_yolov8s_ca_v5/weights/best.pt",
        )
    return w


def parse_args():
    p = argparse.ArgumentParser(description="VM PyTorch herb detection test")
    p.add_argument("--herb", choices=["gouqi", "baizhi", "both"], default="both")
    p.add_argument("--source", default="", help="图片路径，留空用摄像头")
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--device", default="", help="cpu / 0 / cuda:0")
    p.add_argument("--conf", type=float, default=0.25, help="显示阈值")
    p.add_argument("--infer-conf", type=float, default=0.01, help="推理阈值")
    p.add_argument("--save", default="vm_result.jpg")
    return p.parse_args()


def run_one(model: YOLO, frame: np.ndarray, label: str, color, infer_conf: float, disp_conf: float):
    r = model.predict(frame, conf=infer_conf, iou=0.45, verbose=False)[0]
    vis = frame.copy()
    raw = 0.0
    n_show = 0
    if r.boxes is not None and len(r.boxes):
        raw = float(r.boxes.conf.max())
        for box in r.boxes:
            sc = float(box.conf)
            if sc < disp_conf:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            cv2.putText(vis, f"{label} {sc:.2f}", (x1, max(y1 - 6, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            n_show += 1
    return vis, f"{label} raw={raw:.2f} show={n_show}"


def main():
    args = parse_args()
    weights = resolve_weights(args.herb)
    device = args.device or ("0" if __import__("torch").cuda.is_available() else "cpu")

    models: dict[str, YOLO] = {}
    colors = {"gouqi": (0, 140, 255), "baizhi": (0, 180, 0)}
    labels = {"gouqi": "枸杞", "baizhi": "白芷"}

    for name, wp in weights.items():
        models[name] = YOLO(str(wp))
        print(f"已加载 {labels[name]}: {wp} | device={device}")

    if args.source:
        img = cv2.imread(args.source)
        if img is None:
            raise FileNotFoundError(args.source)
        vis = img.copy()
        parts = []
        for name, model in models.items():
            v, st = run_one(model, img, labels[name], colors[name], args.infer_conf, args.conf)
            vis = v
            parts.append(st)
        cv2.imwrite(args.save, vis)
        print(f"保存: {args.save} | {' | '.join(parts)}")
        return

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开摄像头 {args.camera}（VM 需在 VMware 启用 USB 摄像头）")
    print(f"摄像头 {args.camera} | herb={args.herb} | 按 Q 退出")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        vis = frame.copy()
        parts = []
        for name, model in models.items():
            vis, st = run_one(model, vis, labels[name], colors[name], args.infer_conf, args.conf)
            parts.append(st)
        cv2.putText(vis, " | ".join(parts), (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
        cv2.imshow(f"VM test {args.herb}", vis)
        if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
