#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从摄像头采集枸杞样本，用于提升摄像头识别置信度。

采集的图片保存到 gouqi/dataset/images/train，标注为整图框（与初始数据一致）。
建议：手持枸杞，多角度、不同距离，采集 30~50 张。

用法:
    python gouqi/scripts/collect_camera_samples.py --camera 0 --frames 30
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
LABEL = "0 0.5 0.5 1.0 1.0\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--frames", type=int, default=30)
    p.add_argument("--prefix", default="cam")
    args = p.parse_args()

    img_dir = ROOT / "gouqi/dataset/images/train"
    lbl_dir = ROOT / "gouqi/dataset/labels/train"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    existing = len(list(img_dir.glob(f"{args.prefix}_*.jpg")))
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开摄像头 {args.camera}")

    print(f"按 空格 采集，Q 退出，目标 {args.frames} 张")
    saved = 0
    while saved < args.frames:
        ok, frame = cap.read()
        if not ok:
            break
        show = frame.copy()
        cv2.putText(show, f"cam {saved}/{args.frames} SPACE=save Q=quit", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("采集枸杞样本", show)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q")):
            break
        if key == ord(" "):
            idx = existing + saved
            name = f"{args.prefix}_{idx:04d}.jpg"
            cv2.imwrite(str(img_dir / name), frame)
            (lbl_dir / f"{args.prefix}_{idx:04d}.txt").write_text(LABEL, encoding="utf-8")
            saved += 1
            print(f"已保存 {name}")

    cap.release()
    cv2.destroyAllWindows()
    cache = ROOT / "gouqi/dataset/labels/train.cache"
    if cache.exists():
        cache.unlink()
    print(f"共采集 {saved} 张 -> gouqi/dataset/images/train")
    print("下一步: python gouqi/scripts/finetune_camera.py --device 0")


if __name__ == "__main__":
    main()
