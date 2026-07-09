#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RK3588 药材检测引擎 — infer_camera 与 GUI 共用。"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from yolov8_postprocess import filter_by_area, output_tensor_peak, postprocess_yolov8, scale_boxes

try:
    from baizhi.scripts.utils_plot import draw_chinese_boxes, shrink_boxes_xyxy
except ImportError:
    draw_chinese_boxes = None
    shrink_boxes_xyxy = None


def letterbox(im: np.ndarray, new_shape: int = 640, color=(114, 114, 114)):
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


@dataclass
class HerbModel:
    name: str
    label: str
    display: str
    conf: float
    confirm: int
    min_area: float
    max_area: float
    large_area: float
    large_conf: float
    box_shrink: float
    max_det: int
    color: tuple[int, int, int]
    rknn_path: Path
    runtime: object = None
    streak: int = 0
    last_boxes: np.ndarray | None = None
    last_scores: np.ndarray | None = None


@dataclass
class DetectItem:
    name: str
    confidence: float
    bbox: list[int]
    color: tuple[int, int, int] = (0, 180, 0)
    model_key: str = ""


@dataclass
class FrameResult:
    vis: np.ndarray
    items: list[DetectItem] = field(default_factory=list)
    status: str = ""
    raw: float = 0.0


def load_cfg(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def init_rknn(rknn_path: Path):
    try:
        from rknnlite.api import RKNNLite
    except ImportError as e:
        raise ImportError("板端缺少 rknnlite2。请运行: bash rk3588/setup_board.sh") from e
    if not rknn_path.is_file():
        raise FileNotFoundError(f"未找到 RKNN 模型: {rknn_path}")
    rt = RKNNLite()
    if rt.load_rknn(str(rknn_path)) != 0:
        raise RuntimeError(f"load_rknn failed: {rknn_path}")
    if rt.init_runtime() != 0:
        raise RuntimeError("init_runtime failed")
    return rt


def infer_one(
    model: HerbModel,
    frame: np.ndarray,
    *,
    imgsz: int,
    infer_conf: float,
    iou: float,
    max_det: int,
    min_area: float,
    max_area: float,
    large_area: float,
    large_conf: float,
    max_score: float,
) -> tuple[np.ndarray, np.ndarray, float, int, int, float]:
    det_limit = model.max_det if model.max_det > 0 else max_det
    h0, w0 = frame.shape[:2]
    area_min = model.min_area if model.min_area > 0 else min_area
    area_max = model.max_area if model.max_area > 0 else max_area
    la_ratio = model.large_area if model.large_area > 0 else large_area
    la_conf = model.large_conf if model.large_conf > 0 else large_conf

    lb, ratio_pad = letterbox(frame, imgsz)
    rgb = cv2.cvtColor(lb, cv2.COLOR_BGR2RGB)
    outputs = model.runtime.inference(inputs=[np.expand_dims(rgb, 0)])
    tmax = output_tensor_peak(outputs, nc=1)
    boxes, scores = postprocess_yolov8(
        outputs, infer_conf, iou, nc=1, max_det=det_limit, input_size=imgsz,
    )
    raw_max = float(scores.max()) if len(scores) else tmax
    n_cand = len(scores)
    if max_score > 0 and raw_max >= max_score:
        return np.zeros((0, 4)), np.zeros((0,)), raw_max, n_cand, 0, tmax
    if len(boxes) == 0:
        return boxes, scores, raw_max, n_cand, 0, tmax

    boxes = scale_boxes(boxes, (h0, w0), imgsz, ratio_pad=ratio_pad)
    conf_mask = scores >= model.conf
    n_pass = int(conf_mask.sum())
    boxes = boxes[conf_mask]
    scores = scores[conf_mask]
    if max_score > 0 and len(scores):
        ok = scores < max_score
        boxes, scores = boxes[ok], scores[ok]

    if len(boxes):
        filtered, fscores = filter_by_area(
            boxes, scores, (h0, w0), area_min, area_max, la_ratio, la_conf,
        )
        if len(filtered) == 0 and len(boxes):
            areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1]) / (h0 * w0)
            order = scores.argsort()[::-1]
            for i in order:
                if area_min > 0 and areas[i] < area_min:
                    continue
                if areas[i] > 0.85:
                    continue
                filtered = boxes[i : i + 1]
                fscores = scores[i : i + 1]
                break
        boxes, scores = filtered, fscores

    return boxes, scores, raw_max, n_cand, n_pass, tmax


def build_models(cfg: dict, herb: str, base_dir: Path | None = None) -> list[HerbModel]:
    base = base_dir or HERE
    models_cfg = cfg.get("models", {})
    names = ["gouqi", "baizhi"] if herb == "both" else [herb]
    out: list[HerbModel] = []
    for name in names:
        mc = models_cfg.get(name, {})
        rknn = base / mc.get("rknn", f"artifacts/{name}_rk3588.rknn")
        color = mc.get("color_bgr", [0, 180, 0])
        out.append(
            HerbModel(
                name=name,
                label=mc.get("class_name", name),
                display=str(mc.get("display_name", name)),
                conf=float(mc.get("conf", 0.5)),
                confirm=int(mc.get("confirm_frames", 0)),
                min_area=float(mc.get("min_area_ratio", 0.0)),
                max_area=float(mc.get("max_area_ratio", 0.0)),
                large_area=float(mc.get("large_area_ratio", 0.0)),
                large_conf=float(mc.get("large_area_min_conf", 0.0)),
                box_shrink=float(mc.get("box_shrink", 1.0)),
                max_det=int(mc.get("max_det", 0)),
                color=(int(color[0]), int(color[1]), int(color[2])),
                rknn_path=rknn,
            )
        )
    return out


def resolve_camera(cli_value: str | None, cfg_value) -> str | int:
    val = cli_value if cli_value is not None else cfg_value
    if isinstance(val, str):
        s = val.strip()
        if s.startswith("/dev/"):
            return s
        if s.isdigit():
            return int(s)
        return s
    return int(val)


def open_camera(device: str | int):
    cap = cv2.VideoCapture(device)
    if not cap.isOpened() and isinstance(device, int):
        cap = cv2.VideoCapture(f"/dev/video{device}")
    return cap


def _draw_boxes_cv2(frame, boxes, scores, label, color):
    for box, sc in zip(boxes, scores):
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame, f"{label} {sc:.2f}", (x1, max(y1 - 8, 0)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
        )


class HerbEngine:
    """多模型 RKNN 推理引擎。"""

    def __init__(self, cfg_path: str | Path, herb: str = "both"):
        self.cfg_path = Path(cfg_path)
        self.herb = herb
        self.cfg = load_cfg(self.cfg_path)
        inf = self.cfg.get("inference", {})
        self.imgsz = int(inf.get("imgsz", 640))
        self.infer_conf = float(inf.get("infer_conf", 0.01))
        self.iou = float(inf.get("iou", 0.45))
        self.max_det = int(inf.get("max_det", 20))
        self.min_area = float(inf.get("min_area_ratio", 0.0))
        self.max_area = float(inf.get("max_area_ratio", 0.0))
        self.large_area = float(inf.get("large_area_ratio", 0.0))
        self.large_conf = float(inf.get("large_area_min_conf", 0.0))
        self.max_score = float(inf.get("max_score", 0.999))
        self.use_chinese = draw_chinese_boxes is not None
        self.models: list[HerbModel] = []
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        self.models = build_models(self.cfg, self.herb, HERE)
        for m in self.models:
            m.runtime = init_rknn(m.rknn_path)
        self._loaded = True

    def release(self) -> None:
        for m in self.models:
            if m.runtime is not None:
                m.runtime.release()
                m.runtime = None
        self._loaded = False

    def process_frame(self, frame: np.ndarray) -> FrameResult:
        if not self._loaded:
            self.load()
        vis = frame.copy()
        items: list[DetectItem] = []
        status_parts: list[str] = []
        raw_peak = 0.0

        for m in self.models:
            boxes, scores, raw, _n_cand, n_pass, _tmax = infer_one(
                m, frame, imgsz=self.imgsz, infer_conf=self.infer_conf, iou=self.iou,
                max_det=self.max_det, min_area=self.min_area, max_area=self.max_area,
                large_area=self.large_area, large_conf=self.large_conf, max_score=self.max_score,
            )
            raw_peak = max(raw_peak, raw)
            if len(boxes):
                m.streak += 1
                m.last_boxes, m.last_scores = boxes, scores
            else:
                m.streak = 0
                m.last_boxes, m.last_scores = None, None

            show_b = np.zeros((0, 4))
            show_s = np.zeros((0,))
            if m.last_boxes is not None and (m.confirm <= 0 or m.streak >= m.confirm):
                show_b, show_s = m.last_boxes, m.last_scores

            if len(show_b) and m.box_shrink < 1.0 and shrink_boxes_xyxy is not None:
                show_b = shrink_boxes_xyxy(show_b, m.box_shrink, frame.shape)

            if len(show_b):
                labels = [f"{m.label} {sc:.2f}" for sc in show_s]
                if self.use_chinese and draw_chinese_boxes is not None:
                    vis = draw_chinese_boxes(vis, show_b, labels, color=m.color)
                else:
                    _draw_boxes_cv2(vis, show_b, show_s, m.display, m.color)
                for box, sc in zip(show_b, show_s):
                    x1, y1, x2, y2 = map(int, box)
                    items.append(
                        DetectItem(
                            name=m.label,
                            confidence=float(sc),
                            bbox=[x1, y1, x2, y2],
                            color=m.color,
                            model_key=m.name,
                        )
                    )
            status_parts.append(f"{m.label} raw={raw:.2f} pass={n_pass} det={len(show_b)}")

        return FrameResult(
            vis=vis,
            items=items,
            status=" | ".join(status_parts),
            raw=raw_peak,
        )
