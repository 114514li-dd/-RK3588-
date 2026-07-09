"""白芷 YOLOv8 检测主流程（图像 / 视频 / 摄像头）。"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .config import BaizhiDetectConfig
from .inferencer import YoloBaizhiInferencer
from .postprocess import parse_ultralytics_result
from .preprocess import load_image, preprocess_frame
from .types import BaizhiDetectResult
from .visualizer import draw_result


class BaizhiDetector:
    """YOLOv8 + OpenCV 白芷检测器 — 对外统一 API。"""

    def __init__(self, cfg: BaizhiDetectConfig | None = None):
        self.cfg = cfg or BaizhiDetectConfig()
        self._inferencer: YoloBaizhiInferencer | None = None

    @property
    def inferencer(self) -> YoloBaizhiInferencer:
        if self._inferencer is None:
            self._inferencer = YoloBaizhiInferencer(self.cfg)
        return self._inferencer

    def detect_image(self, path: str | Path) -> BaizhiDetectResult:
        """检测单张图片（OpenCV 读取 + YOLOv8 推理 + 结果解析）。"""
        img = load_image(path)
        if img is None:
            return BaizhiDetectResult.failure(f"无法读取图片: {path}")
        return self.detect_frame(img)

    def detect_frame(self, frame_bgr: np.ndarray, *, use_raw_infer: bool = False) -> BaizhiDetectResult:
        """检测单帧 BGR 图像。"""
        if frame_bgr is None or frame_bgr.size == 0:
            return BaizhiDetectResult.failure("空图像帧")

        processed = preprocess_frame(frame_bgr, self.cfg)
        if use_raw_infer:
            results = self.inferencer.infer_raw(processed, conf=0.01)
        else:
            results = self.inferencer.infer(processed)

        if not results:
            h, w = processed.shape[:2]
            return BaizhiDetectResult(success=True, count=0, boxes=[], image_width=w, image_height=h)

        return parse_ultralytics_result(results[0], self.cfg, processed)

    def detect_and_draw(self, frame_bgr: np.ndarray) -> tuple[BaizhiDetectResult, np.ndarray]:
        """检测并返回可视化图像。"""
        result = self.detect_frame(frame_bgr)
        vis = draw_result(frame_bgr.copy(), result, self.cfg)
        return result, vis

    def detect_image_and_save(
        self,
        path: str | Path,
        save_path: str | Path,
    ) -> BaizhiDetectResult:
        """检测图片并保存带框结果。"""
        img = load_image(path)
        if img is None:
            return BaizhiDetectResult.failure(f"无法读取图片: {path}")

        result, vis = self.detect_and_draw(img)
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(save_path), vis)
        return result
