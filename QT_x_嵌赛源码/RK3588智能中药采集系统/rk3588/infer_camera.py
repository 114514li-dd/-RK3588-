#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RK3588 板端摄像头检测 — 枸杞 / 白芷 / 双类（与 Windows balanced 对齐）。"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import yaml

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from herb_engine import HerbEngine, open_camera, resolve_camera


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RK3588 herb camera detection")
    p.add_argument("--herb", choices=["gouqi", "baizhi", "both"], default="gouqi")
    p.add_argument("--cfg", default=str(HERE / "deploy.yaml"))
    p.add_argument("--camera", type=str, default=None)
    p.add_argument("--source", default="", help="图片路径，留空则用摄像头")
    p.add_argument("--save", default="result.jpg")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = yaml.safe_load(open(args.cfg, encoding="utf-8"))
    inf = cfg.get("inference", {})
    infer_every = max(int(inf.get("infer_every", 3)), 1)
    max_fps = float(inf.get("max_fps", 20.0))
    min_interval = 1.0 / max(max_fps, 1.0)
    camera = resolve_camera(args.camera, inf.get("camera", 0))
    cam_w = int(inf.get("cam_width", 640))
    cam_h = int(inf.get("cam_height", 480))

    engine = HerbEngine(args.cfg, herb=args.herb)
    engine.load()
    for m in engine.models:
        print(f"已加载 {m.label}: {m.rknn_path} conf>={m.conf} shrink={m.box_shrink}")

    if args.source:
        img = cv2.imread(args.source)
        if img is None:
            raise FileNotFoundError(args.source)
        result = engine.process_frame(img)
        cv2.imwrite(args.save, result.vis)
        print(f"保存: {args.save} | {result.status}")
        engine.release()
        return

    cap = open_camera(camera)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开摄像头 {camera}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_h)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    print(f"摄像头 {camera} | herb={args.herb} | infer每{infer_every}帧 | 按 Q 退出")

    frame_idx = 0
    last_vis, last_status = None, ""
    last_infer_t = 0.0
    while True:
        loop_start = time.time()
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1
        if frame_idx % infer_every == 0 and (loop_start - last_infer_t >= min_interval):
            result = engine.process_frame(frame)
            last_vis, last_status = result.vis, result.status
            last_infer_t = time.time()
        show = last_vis if last_vis is not None else frame
        if last_status:
            cv2.putText(
                show, last_status, (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2,
            )
        cv2.imshow(f"RK3588 {args.herb}", show)
        if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
            break
        elapsed = time.time() - loop_start
        sleep_t = min_interval - elapsed
        if sleep_t > 0:
            time.sleep(sleep_t)

    cap.release()
    cv2.destroyAllWindows()
    engine.release()


if __name__ == "__main__":
    main()
