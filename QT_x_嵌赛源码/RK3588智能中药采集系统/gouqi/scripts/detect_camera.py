#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""枸杞检测 — 摄像头实时推理（同白芷流程）。"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baizhi.scripts.rotation_tta import predict_with_rotation
from baizhi.scripts.utils_plot import draw_chinese_boxes, shrink_boxes_xyxy
from ultralytics import YOLO


def check_rtx50_gpu_env(device: str) -> None:
    import torch

    use_cuda = device not in {"", "cpu"} or (not device and torch.cuda.is_available())
    if not use_cuda or not torch.cuda.is_available():
        return
    cap = torch.cuda.get_device_capability()
    arch = torch.cuda.get_arch_list()
    if cap >= (12, 0) and "sm_120" not in arch:
        print("\n请改用 baizhi 环境: conda activate baizhi")
        sys.exit(1)


def default_weights() -> str:
    for name in ("gouqi_yolov8s_ca_v6", "gouqi_yolov8s_ca_v5", "gouqi_yolov8s_ca_v4", "gouqi_yolov8s_ca_v3", "gouqi_yolov8s_ca_v2", "gouqi_yolov8s_ca"):
        p = ROOT / f"gouqi/runs/detect/{name}/weights/best.pt"
        if p.exists():
            return str(p)
    return str(ROOT / "gouqi/runs/detect/gouqi_yolov8s_ca/weights/best.pt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gouqi realtime camera detection")
    parser.add_argument("--weights", type=str, default=default_weights())
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--mode", type=str, default="balanced", choices=["balanced", "strict"])
    parser.add_argument("--conf", type=float, default=None)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument("--imgsz", type=int, default=640, help="主推理尺寸")
    parser.add_argument("--imgsz-extra", type=str, default="", help="多尺度推理，逗号分隔，留空关闭(默认关，更流畅)")
    parser.add_argument("--rotate", action="store_true", default=False, help="四方向推理，更准但更卡")
    parser.add_argument("--no-rotate", action="store_false", dest="rotate")
    parser.add_argument("--device", type=str, default="")
    parser.add_argument("--min-area", type=float, default=None)
    parser.add_argument("--max-area", type=float, default=None)
    parser.add_argument("--confirm", type=int, default=None)
    parser.add_argument("--max-det", type=int, default=5)
    parser.add_argument("--max-fps", type=float, default=20.0)
    parser.add_argument("--infer-every", type=int, default=3)
    parser.add_argument("--cam-width", type=int, default=640)
    parser.add_argument("--cam-height", type=int, default=480)
    parser.add_argument("--hold-ms", type=int, default=0)
    parser.add_argument("--box-shrink", type=float, default=0.65)
    return parser.parse_args()


def filter_boxes(boxes, frame_shape: tuple, min_area: float, max_area: float):
    if boxes is None or len(boxes) == 0:
        return None
    h, w = frame_shape[:2]
    frame_area = h * w
    xyxy = boxes.xyxy.cpu().numpy()
    confs = boxes.conf.cpu().numpy()
    keep_xyxy, keep_conf = [], []
    for box, conf in zip(xyxy, confs):
        x1, y1, x2, y2 = box
        area_ratio = (x2 - x1) * (y2 - y1) / frame_area
        if min_area > 0 and area_ratio < min_area:
            continue
        if max_area > 0 and area_ratio > max_area:
            continue
        keep_xyxy.append(box)
        keep_conf.append(conf)
    if not keep_xyxy:
        return None
    return np.array(keep_xyxy), np.array(keep_conf)


def apply_mode_defaults(args) -> None:
    presets = {
        "balanced": {"conf": 0.40, "min_area": 0.0, "max_area": 0.0, "confirm": 0},
        "strict": {"conf": 0.75, "min_area": 0.02, "max_area": 0.85, "confirm": 3},
    }
    p = presets[args.mode]
    if args.conf is None:
        args.conf = p["conf"]
    if args.min_area is None:
        args.min_area = p["min_area"]
    if args.max_area is None:
        args.max_area = p["max_area"]
    if args.confirm is None:
        args.confirm = p["confirm"]


def use_half(device: str) -> bool:
    import torch

    if device == "cpu":
        return False
    return torch.cuda.is_available()


def main() -> None:
    args = parse_args()
    apply_mode_defaults(args)
    check_rtx50_gpu_env(args.device)
    if not Path(args.weights).exists():
        print(f"未找到权重: {args.weights}")
        print("请先运行: 启动枸杞训练.bat")
        sys.exit(1)
    model = YOLO(args.weights)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开摄像头 index={args.camera}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.cam_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.cam_height)

    label_cn = "枸杞"
    hit_streak = 0
    last_boxes = None
    last_show = None
    last_infer_has_det = False
    last_detect_t = 0.0
    frame_idx = 0
    min_interval = 1.0 / max(args.max_fps, 1.0)
    hold_sec = max(args.hold_ms, 0) / 1000.0
    half = use_half(args.device)
    print(f"枸杞检测 | mode={args.mode} | conf={args.conf} | infer每{args.infer_every}帧 | rotate={args.rotate}")
    print(f"权重: {args.weights}")
    print("按 Q 退出")
    imgsz_list = [args.imgsz]
    if args.imgsz_extra.strip():
        imgsz_list.extend(int(x) for x in args.imgsz_extra.split(",") if x.strip())
    imgsz_list = sorted(set(imgsz_list))

    raw_max_conf = 0.0
    prev = time.time()
    last_infer_t = 0.0

    while True:
        loop_start = time.time()
        ok, frame = cap.read()
        if not ok:
            break

        frame_idx += 1
        do_infer = (frame_idx % max(args.infer_every, 1) == 0) and (loop_start - last_infer_t >= min_interval)

        if do_infer:
            def once(model, img, imgsz: int):
                r = filter_boxes(
                    model.predict(
                        source=img, imgsz=imgsz, conf=0.01, iou=args.iou,
                        device=args.device, max_det=args.max_det, verbose=False, half=half,
                    )[0].boxes,
                    img.shape, args.min_area, args.max_area,
                )
                if r is None:
                    return None
                xy, cf = r
                return xy, cf, np.zeros(len(cf), dtype=int)

            merged_xy, merged_cf = [], []
            for sz in imgsz_list:
                if args.rotate:
                    raw = predict_with_rotation(model, frame, lambda m, im: once(m, im, sz), enable=True)
                else:
                    raw = once(model, frame, sz)
                if raw is None:
                    continue
                xy, cf, _ = raw
                merged_xy.append(xy)
                merged_cf.append(cf)
            if merged_xy:
                xy = np.concatenate(merged_xy)
                cf = np.concatenate(merged_cf)
                from baizhi.scripts.rotation_tta import nms_keep_best

                if len(imgsz_list) > 1 or args.rotate:
                    keep = nms_keep_best(xy, cf, 0.45)
                    xy, cf = xy[keep], cf[keep]
                raw_max_conf = float(cf.max()) if len(cf) else 0.0
                keep = cf >= args.conf
                boxes = (xy[keep], cf[keep]) if keep.any() else None
            else:
                raw_max_conf = 0.0
                boxes = None
            last_infer_t = time.time()

            if boxes is not None:
                hit_streak += 1
                last_boxes = boxes
            else:
                hit_streak = 0

            show_boxes = boxes
            if args.confirm > 0:
                show_boxes = last_boxes if hit_streak >= args.confirm else None

            last_infer_has_det = show_boxes is not None
            if last_infer_has_det:
                last_show = show_boxes
                last_detect_t = time.time()
            elif hold_sec <= 0:
                last_show = None
        else:
            if not last_infer_has_det:
                last_show = None
            elif hold_sec > 0 and (time.time() - last_detect_t > hold_sec):
                last_show = None

        show_boxes = last_show
        if show_boxes is not None:
            xyxy, confs = show_boxes
            xyxy = shrink_boxes_xyxy(xyxy, args.box_shrink, frame.shape)
            labels = [f"{label_cn} {c:.2f}" for c in confs]
            frame = draw_chinese_boxes(frame, xyxy, labels)

        fps = 1.0 / max(time.time() - prev, 1e-6)
        prev = time.time()
        cv2.putText(
            frame, f"枸杞 {fps:.1f}fps conf>={args.conf} raw={raw_max_conf:.2f}",
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2,
        )
        cv2.imshow("枸杞检测 - 按Q退出", frame)
        if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
            break

        elapsed = time.time() - loop_start
        sleep_t = min_interval - elapsed
        if sleep_t > 0:
            time.sleep(sleep_t)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
