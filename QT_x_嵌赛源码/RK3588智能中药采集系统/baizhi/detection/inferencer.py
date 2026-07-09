"""YOLOv8 白芷推理模块。"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ultralytics.engine.results import Results

from .config import BaizhiDetectConfig


class YoloBaizhiInferencer:
    """加载 YOLOv8 权重并执行推理（内置 NMS，通过 conf/iou 控制）。"""

    def __init__(self, cfg: BaizhiDetectConfig):
        from ultralytics import YOLO

        self.cfg = cfg
        self.model = YOLO(cfg.weights)
        self.model.overrides["conf"] = cfg.conf
        self.model.overrides["iou"] = cfg.iou

    def infer(self, source: np.ndarray | str) -> list[Results]:
        """对单帧 BGR 数组或图片路径推理。"""
        return self.model.predict(
            source=source,
            imgsz=self.cfg.imgsz,
            conf=self.cfg.conf,
            iou=self.cfg.iou,
            device=self.cfg.device,
            max_det=self.cfg.max_det,
            verbose=False,
        )

    def infer_raw(self, source: np.ndarray | str, conf: float | None = None) -> list[Results]:
        """低阈值推理，供后处理模块二次过滤（摄像头抗误检场景）。"""
        low_conf = conf if conf is not None else min(self.cfg.conf, 0.01)
        return self.model.predict(
            source=source,
            imgsz=self.cfg.imgsz,
            conf=low_conf,
            iou=self.cfg.iou,
            device=self.cfg.device,
            max_det=self.cfg.max_det,
            verbose=False,
        )
