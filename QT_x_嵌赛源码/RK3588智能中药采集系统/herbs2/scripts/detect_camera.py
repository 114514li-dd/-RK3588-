#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""白芷 + 枸杞 双类摄像头检测。

默认 --ensemble：两个单类模型并行推理（摄像头效果优于单一双类模型）。
可选 --backend dual：使用 herbs2 双类权重。
"""

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

from baizhi.detection import filter_baizhi_fp, resolve_default_weights
from baizhi.scripts.rotation_tta import nms_keep_best, predict_with_rotation
from baizhi.scripts.utils_plot import draw_chinese_boxes, shrink_boxes_xyxy
from ultralytics import YOLO

CLASS_CN = {0: "白芷", 1: "枸杞"}
CLASS_COLOR = {0: (0, 180, 0), 1: (255, 140, 0)}


def check_rtx50_gpu_env(device: str) -> None:
    import torch

    use_cuda = device not in {"", "cpu"} or (not device and torch.cuda.is_available())
    if not use_cuda or not torch.cuda.is_available():
        return
    cap = torch.cuda.get_device_capability()
    arch = torch.cuda.get_arch_list()
    if cap >= (12, 0) and "sm_120" not in arch:
        print("请改用 baizhi 环境: conda activate baizhi")
        sys.exit(1)


def default_baizhi_weights() -> str:
    return resolve_default_weights()


def default_gouqi_weights() -> str:
    for name in ("gouqi_yolov8s_ca_v6", "gouqi_yolov8s_ca_v5", "gouqi_yolov8s_ca_v4", "gouqi_yolov8s_ca_v3", "gouqi_yolov8s_ca_v2", "gouqi_yolov8s_ca"):
        p = ROOT / f"gouqi/runs/detect/{name}/weights/best.pt"
        if p.exists():
            return str(p)
    return str(ROOT / "gouqi/runs/detect/gouqi_yolov8s_ca/weights/best.pt")


def default_dual_weights() -> str:
    return str(ROOT / "herbs2/runs/detect/herbs2_yolov8s_ca/weights/best.pt")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Baizhi + Gouqi camera detection")
    p.add_argument("--backend", choices=["ensemble", "dual"], default="ensemble", help="ensemble=双单类并行(推荐)")
    p.add_argument("--weights-baizhi", default=default_baizhi_weights())
    p.add_argument("--weights-gouqi", default=default_gouqi_weights())
    p.add_argument("--weights", default=default_dual_weights(), help="dual 模式用")
    p.add_argument("--conf-baizhi", type=float, default=0.50, help="白芷显示阈值，低于此分数不画框")
    p.add_argument("--conf-gouqi", type=float, default=0.40, help="枸杞显示阈值，低于此分数不画框")
    p.add_argument("--confirm-baizhi", type=int, default=2, help="白芷连续N帧确认后才画框，0=关闭")
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--mode", default="balanced", choices=["balanced", "strict"])
    p.add_argument("--conf", type=float, default=None, help="dual 模式全局 conf")
    p.add_argument("--iou", type=float, default=0.45)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--device", default="0")
    p.add_argument("--min-area", type=float, default=0.0)
    p.add_argument("--max-area", type=float, default=0.0)
    p.add_argument("--max-det", type=int, default=10)
    p.add_argument("--max-fps", type=float, default=20.0)
    p.add_argument("--infer-every", type=int, default=3)
    p.add_argument("--cam-width", type=int, default=640)
    p.add_argument("--cam-height", type=int, default=480)
    p.add_argument("--hold-ms", type=int, default=0, help="检测丢失后框保留毫秒，0=立刻消失")
    p.add_argument("--box-shrink", type=float, default=0.65)
    p.add_argument("--debug", action="store_true")
    p.add_argument("--imgsz-extra", type=str, default="", help="枸杞多尺度，留空关闭(默认关，更流畅)")
    p.add_argument("--gouqi-rotate", action="store_true", default=False, help="枸杞四方向推理，更准但更卡")
    p.add_argument("--no-gouqi-rotate", action="store_false", dest="gouqi_rotate")
    return p.parse_args()


def apply_mode_defaults(args) -> None:
    if args.backend == "ensemble":
        if args.mode == "strict":
            args.conf_baizhi = max(args.conf_baizhi, 0.55)
            args.conf_gouqi = max(args.conf_gouqi, 0.55)
        return
    presets = {
        "balanced": {"conf": 0.20},
        "strict": {"conf": 0.55},
    }
    if args.conf is None:
        args.conf = presets[args.mode]["conf"]


def filter_boxes(boxes, frame_shape, min_area, max_area, cls_id: int):
    if boxes is None or len(boxes) == 0:
        return None
    h, w = frame_shape[:2]
    area = h * w
    xyxy = boxes.xyxy.cpu().numpy()
    confs = boxes.conf.cpu().numpy()
    keep_xy, keep_cf, keep_cls = [], [], []
    for box, conf in zip(xyxy, confs):
        x1, y1, x2, y2 = box
        r = (x2 - x1) * (y2 - y1) / area
        if min_area > 0 and r < min_area:
            continue
        if max_area > 0 and r > max_area:
            continue
        keep_xy.append(box)
        keep_cf.append(conf)
        keep_cls.append(cls_id)
    if not keep_xy:
        return None
    return np.array(keep_xy), np.array(keep_cf), np.array(keep_cls)


def merge_boxes(parts: list):
    valid = [p for p in parts if p is not None]
    if not valid:
        return None
    xy = np.concatenate([p[0] for p in valid])
    cf = np.concatenate([p[1] for p in valid])
    cl = np.concatenate([p[2] for p in valid])
    return xy, cf, cl


def draw_dual_boxes(frame, xyxy, confs, clss, box_shrink):
    xyxy = shrink_boxes_xyxy(xyxy, box_shrink, frame.shape)
    for box, conf, cls_id in zip(xyxy, confs, clss):
        name = CLASS_CN.get(int(cls_id), f"cls{cls_id}")
        color = CLASS_COLOR.get(int(cls_id), (0, 180, 0))
        frame = draw_chinese_boxes(frame, box.reshape(1, 4), [f"{name} {conf:.2f}"], color=color)
    return frame


def use_half(device: str) -> bool:
    import torch

    if device == "cpu":
        return False
    return torch.cuda.is_available()


def predict_ensemble(models, frame, args, half: bool = False):
    imgsz_list = [args.imgsz]
    if args.imgsz_extra.strip():
        imgsz_list.extend(int(x) for x in args.imgsz_extra.split(",") if x.strip())
    imgsz_list = sorted(set(imgsz_list))

    def once_baizhi(model, img):
        raw_boxes = model.predict(
            source=img, imgsz=args.imgsz, conf=0.01, iou=args.iou,
            device=args.device, max_det=args.max_det, verbose=False, half=half,
        )[0].boxes
        raw_max = float(raw_boxes.conf.max()) if raw_boxes is not None and len(raw_boxes) else 0.0
        raw = filter_boxes(raw_boxes, img.shape, args.min_area, args.max_area, cls_id=0)
        if raw is None:
            return None, raw_max
        fp = filter_baizhi_fp(raw[0], raw[1], img.shape, args.conf_baizhi)
        if fp is None:
            return None, raw_max
        xyxy, confs = fp
        return (xyxy, confs, np.zeros(len(confs), dtype=int)), raw_max

    def once_gouqi(model, img, imgsz: int):
        return filter_boxes(
            model.predict(
                source=img, imgsz=imgsz, conf=0.01, iou=args.iou,
                device=args.device, max_det=args.max_det, verbose=False, half=half,
            )[0].boxes,
            img.shape, args.min_area, args.max_area, cls_id=1,
        )

    def run_gouqi(imgsz: int):
        if args.gouqi_rotate:
            return predict_with_rotation(
                models["gouqi"], frame, lambda m, im: once_gouqi(m, im, imgsz), enable=True,
            )
        return once_gouqi(models["gouqi"], frame, imgsz)

    mb, raw_bz = once_baizhi(models["baizhi"], frame)
    merged_xy, merged_cf, merged_cls = [], [], []
    for sz in imgsz_list:
        mg = run_gouqi(sz)
        if mg is None:
            continue
        merged_xy.append(mg[0])
        merged_cf.append(mg[1])
        merged_cls.append(mg[2])
    mg = None
    if merged_xy:
        xy = np.concatenate(merged_xy)
        cf = np.concatenate(merged_cf)
        cl = np.concatenate(merged_cls)
        if len(imgsz_list) > 1 or args.gouqi_rotate:
            keep = nms_keep_best(xy, cf, args.iou)
            xy, cf, cl = xy[keep], cf[keep], cl[keep]
        keep = cf >= args.conf_gouqi
        if keep.any():
            mg = (xy[keep], cf[keep], cl[keep])
    return merge_boxes([mb, mg]), raw_bz


def predict_dual(model, frame, args, half: bool = False):
    raw = model.predict(
        source=frame, imgsz=args.imgsz, conf=args.conf, iou=args.iou,
        device=args.device, max_det=args.max_det, verbose=False, half=half,
    )[0].boxes
    if raw is None or len(raw) == 0:
        return None
    h, w = frame.shape[:2]
    area = h * w
    xyxy = raw.xyxy.cpu().numpy()
    confs = raw.conf.cpu().numpy()
    clss = raw.cls.cpu().numpy().astype(int)
    keep = [
        (box, conf, cls_id)
        for box, conf, cls_id in zip(xyxy, confs, clss)
        if (
            (cls_id == 1 and conf >= args.conf_gouqi)
            or (cls_id != 1 and conf >= args.conf)
        )
        and not (
            (args.min_area > 0 and (box[2] - box[0]) * (box[3] - box[1]) / area < args.min_area)
            or (args.max_area > 0 and (box[2] - box[0]) * (box[3] - box[1]) / area > args.max_area)
        )
    ]
    if not keep:
        return None
    xy, cf, cl = zip(*keep)
    return np.array(xy), np.array(cf), np.array(cl)


def main() -> None:
    args = parse_args()
    apply_mode_defaults(args)
    check_rtx50_gpu_env(args.device)

    models = {}
    if args.backend == "ensemble":
        for name, path in (("baizhi", args.weights_baizhi), ("gouqi", args.weights_gouqi)):
            if not Path(path).exists():
                print(f"未找到 {name} 权重: {path}")
                sys.exit(1)
            models[name] = YOLO(path)
        print("模式: 双单类并行 (白芷模型 + 枸杞模型)")
        print(f"  白芷: {args.weights_baizhi}  conf>={args.conf_baizhi} confirm={args.confirm_baizhi}")
        print(f"  枸杞: {args.weights_gouqi}  conf>={args.conf_gouqi}")
    else:
        if not Path(args.weights).exists():
            print(f"未找到权重: {args.weights}")
            sys.exit(1)
        models["dual"] = YOLO(args.weights)
        print(f"模式: 双类单模型 conf>={args.conf}")
        print(f"  权重: {args.weights}")

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开摄像头 {args.camera}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.cam_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.cam_height)

    last_show = None
    last_baizhi = None
    last_gouqi = None
    baizhi_hit = 0
    last_detect_t = 0.0
    frame_idx = 0
    min_interval = 1.0 / max(args.max_fps, 1.0)
    hold_sec = max(args.hold_ms, 0) / 1000.0
    half = use_half(args.device)
    debug_info = ""
    raw_bz_conf = 0.0
    print(f"流畅模式: 每{args.infer_every}帧推理 | rotate={args.gouqi_rotate} | multi-scale={'开' if args.imgsz_extra.strip() else '关'}")
    print("必须在 ultralytics-main 目录运行，勿在 yolov5-master 下运行")
    print("按 Q 退出")
    prev, last_infer_t = time.time(), 0.0

    while True:
        loop_start = time.time()
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1
        do_infer = (frame_idx % max(args.infer_every, 1) == 0) and (loop_start - last_infer_t >= min_interval)

        if do_infer:
            if args.backend == "ensemble":
                show, raw_bz_conf = predict_ensemble(models, frame, args, half=half)
            else:
                show = predict_dual(models["dual"], frame, args, half=half)
                raw_bz_conf = float(show[1][show[2] == 0].max()) if show is not None and np.any(show[2] == 0) else 0.0
            last_infer_t = time.time()

            if show is not None and np.any(show[2] == 0):
                baizhi_hit += 1
                m = show[2] == 0
                last_baizhi = (show[0][m], show[1][m], show[2][m])
            else:
                baizhi_hit = 0
                last_baizhi = None

            if show is not None and np.any(show[2] == 1):
                m = show[2] == 1
                last_gouqi = (show[0][m], show[1][m], show[2][m])
            elif show is None or not np.any(show[2] == 1):
                last_gouqi = None

            parts = []
            if last_baizhi is not None and (args.confirm_baizhi <= 0 or baizhi_hit >= args.confirm_baizhi):
                parts.append(last_baizhi)
            if last_gouqi is not None:
                parts.append(last_gouqi)
            show = merge_boxes(parts)

            if show is not None:
                last_show = show
                last_detect_t = time.time()
                if args.debug:
                    n_bz = int(np.sum(show[2] == 0))
                    n_gq = int(np.sum(show[2] == 1))
                    debug_info = f"白芷={n_bz} 枸杞={n_gq} bz_raw={raw_bz_conf:.2f}"
            elif hold_sec <= 0 or (time.time() - last_detect_t > hold_sec):
                last_show = None
                if args.debug:
                    debug_info = "无检测"
        elif hold_sec > 0 and last_show is not None and (time.time() - last_detect_t > hold_sec):
            last_show = None

        if last_show is not None:
            frame = draw_dual_boxes(frame, *last_show, args.box_shrink)

        fps = 1.0 / max(time.time() - prev, 1e-6)
        prev = time.time()
        cv2.putText(
            frame,
            f"白芷+枸杞 {fps:.1f}fps bz>={args.conf_baizhi:.2f} raw_bz={raw_bz_conf:.2f}",
            (10, 28),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
        )
        if args.debug and debug_info:
            cv2.putText(frame, debug_info, (10, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        cv2.imshow("白芷+枸杞检测 - 按Q退出", frame)
        if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
            break
        sleep_t = min_interval - (time.time() - loop_start)
        if sleep_t > 0:
            time.sleep(sleep_t)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
