#!/usr/bin/env python3
"""板端 RKNN 诊断：对比黑图/实拍，判断模型是否响应输入。"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from yolov8_postprocess import describe_outputs, detect_postprocess_mode, output_tensor_peak, postprocess_yolov8, scale_boxes


def letterbox(im, new_shape=640, color=(114, 114, 114)):
    h, w = im.shape[:2]
    r = min(new_shape / h, new_shape / w)
    nw, nh = int(round(w * r)), int(round(h * r))
    im_resized = cv2.resize(im, (nw, nh), interpolation=cv2.INTER_LINEAR)
    pad_x = (new_shape - nw) / 2
    pad_y = (new_shape - nh) / 2
    top, left = int(round(pad_y - 0.1)), int(round(pad_x - 0.1))
    out = np.full((new_shape, new_shape, 3), color, dtype=np.uint8)
    out[top : top + nh, left : left + nw] = im_resized
    ratio_pad = ((r, r), (pad_x, pad_y))
    return out, ratio_pad


def run_once(rt, frame, infer_conf, disp_conf):
    lb, ratio_pad = letterbox(frame)
    rgb = cv2.cvtColor(lb, cv2.COLOR_BGR2RGB)
    outputs = rt.inference(inputs=[np.expand_dims(rgb, 0)])
    mode = detect_postprocess_mode(outputs, nc=1)
    tmax = output_tensor_peak(outputs, nc=1)
    boxes, scores = postprocess_yolov8(outputs, infer_conf, 0.45, nc=1, max_det=10, input_size=640)
    show = scores >= disp_conf
    n_det = int(show.sum())
    return outputs, mode, tmax, len(scores), n_det, boxes[show], scores[show], ratio_pad


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--herb", choices=["gouqi", "baizhi"], default="gouqi")
    p.add_argument("--camera", default="/dev/video21")
    p.add_argument("--save", default="/home/elf/rknn_debug.jpg")
    args = p.parse_args()

    cfg = yaml.safe_load(open(HERE / "deploy.yaml", encoding="utf-8"))
    mc = cfg["models"][args.herb]
    rknn_path = HERE / mc["rknn"]
    infer_conf = float(cfg["inference"].get("infer_conf", 0.01))
    disp_conf = float(mc.get("conf", 0.25))

    from rknnlite.api import RKNNLite

    rt = RKNNLite()
    assert rt.load_rknn(str(rknn_path)) == 0, f"load failed: {rknn_path}"
    assert rt.init_runtime() == 0
    print(f"模型: {rknn_path}")

    black = np.zeros((480, 640, 3), dtype=np.uint8)
    cap = cv2.VideoCapture(args.camera)
    ok, live = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"无法读摄像头 {args.camera}")

    out_b, mode_b, tmax_b, n_b, det_b, _, _, _ = run_once(rt, black, infer_conf, disp_conf)
    out_l, mode_l, tmax_l, n_l, det_l, boxes, scores, ratio_pad = run_once(rt, live, infer_conf, disp_conf)

    print("RKNN 输出:", describe_outputs(out_l))
    print(f"后处理模式: {mode_l}")
    print(f"黑图: tmax={tmax_b:.4f} n={n_b} det={det_b}")
    print(f"实拍: tmax={tmax_l:.4f} n={n_l} det={det_l}")

    if out_b and out_l:
        diff = float(np.max(np.abs(np.asarray(out_b[0], dtype=np.float32) - np.asarray(out_l[0], dtype=np.float32))))
        print(f"输出张量最大差值: {diff:.4f}")
        if diff < 0.01:
            print("[!] 黑图与实拍输出几乎相同 → INT8 量化可能已损坏模型")
            print("    请在虚拟机重新导出 FP16: bash rk3588/export_models_wsl.sh fp16")

    vis = live.copy()
    boxes = scale_boxes(boxes, vis.shape[:2], 640, ratio_pad=ratio_pad) if len(boxes) else boxes
    for box, sc in zip(boxes, scores):
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(vis, f"{sc:.2f}", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.imwrite(args.save, vis)
    print(f"保存: {args.save}")
    rt.release()


if __name__ == "__main__":
    main()
