"""摄像头 / 视频流检测（帧率控制、连续帧确认）。"""

from __future__ import annotations

import time
from collections.abc import Iterator

import cv2
import numpy as np

from .config import BaizhiDetectConfig
from .pipeline import BaizhiDetector
from .types import BaizhiDetectResult
from .visualizer import draw_result, draw_status_bar


class VideoStreamTracker:
    """视频流状态：跳帧推理 + 连续帧确认 + 丢失保持。"""

    def __init__(self, cfg: BaizhiDetectConfig):
        self.cfg = cfg
        self.frame_idx = 0
        self.hit_streak = 0
        self.last_boxes_result: BaizhiDetectResult | None = None
        self.last_show: BaizhiDetectResult | None = None
        self.last_infer_has_det = False
        self.last_detect_t = 0.0
        self.last_infer_t = 0.0
        self.min_interval = 1.0 / max(cfg.max_fps, 1.0)
        self.hold_sec = max(cfg.hold_ms, 0) / 1000.0

    def should_infer(self, now: float | None = None) -> bool:
        now = now or time.time()
        self.frame_idx += 1
        every = max(self.cfg.infer_every, 1)
        if self.frame_idx % every != 0:
            return False
        return now - self.last_infer_t >= self.min_interval

    def update(self, result: BaizhiDetectResult, *, inferred: bool) -> BaizhiDetectResult:
        """更新跟踪状态，返回当前应显示的检测结果。"""
        now = time.time()
        if inferred:
            self.last_infer_t = now
            if result.count > 0:
                self.hit_streak += 1
                self.last_boxes_result = result
            else:
                self.hit_streak = 0
                self.last_boxes_result = None

            show = result if result.count > 0 else None
            if self.cfg.confirm_frames > 0:
                show = self.last_boxes_result if self.hit_streak >= self.cfg.confirm_frames else None

            self.last_infer_has_det = show is not None and show.count > 0
            if self.last_infer_has_det and show is not None:
                self.last_show = show
                self.last_detect_t = now
            elif self.hold_sec <= 0:
                self.last_show = None
        else:
            if not self.last_infer_has_det:
                self.last_show = None
            elif self.hold_sec > 0 and (now - self.last_detect_t > self.hold_sec):
                self.last_show = None

        return self.last_show or BaizhiDetectResult(
            success=True,
            count=0,
            boxes=[],
            image_width=result.image_width,
            image_height=result.image_height,
        )


def iter_camera(
    detector: BaizhiDetector,
    camera_index: int = 0,
    width: int = 640,
    height: int = 480,
) -> Iterator[tuple[np.ndarray, BaizhiDetectResult, BaizhiDetectResult]]:
    """摄像头迭代器：yield (可视化帧, 原始推理结果, 显示用结果)。"""
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开摄像头 index={camera_index}")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    tracker = VideoStreamTracker(detector.cfg)
    prev = time.time()

    try:
        while True:
            loop_start = time.time()
            ok, frame = cap.read()
            if not ok:
                break

            do_infer = tracker.should_infer(loop_start)
            if do_infer:
                raw_result = detector.detect_frame(frame, use_raw_infer=True)
            else:
                raw_result = BaizhiDetectResult(
                    success=True,
                    count=0,
                    image_width=frame.shape[1],
                    image_height=frame.shape[0],
                )

            show_result = tracker.update(raw_result if do_infer else raw_result, inferred=do_infer)
            vis = draw_result(frame.copy(), show_result, detector.cfg)

            now = time.time()
            fps = 1.0 / max(now - prev, 1e-6)
            prev = now
            raw_conf = raw_result.best().confidence if raw_result.best() else 0.0
            vis = draw_status_bar(
                vis,
                show_result,
                fps=fps,
                extra=f"conf>={detector.cfg.conf:.2f} raw={raw_conf:.2f}",
            )

            yield vis, raw_result, show_result

            elapsed = time.time() - loop_start
            sleep_t = tracker.min_interval - elapsed
            if sleep_t > 0:
                time.sleep(sleep_t)
    finally:
        cap.release()


def run_camera_loop(
    detector: BaizhiDetector,
    camera_index: int = 0,
    window_name: str = "白芷检测 - 按Q退出",
    width: int = 640,
    height: int = 480,
) -> None:
    """阻塞式摄像头检测窗口。"""
    for vis, _, _ in iter_camera(detector, camera_index, width=width, height=height):
        cv2.imshow(window_name, vis)
        if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
            break
    cv2.destroyAllWindows()
