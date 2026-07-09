"""白芷 YOLOv8 + OpenCV 模块化检测包。"""

from .config import BaizhiDetectConfig, resolve_default_weights
from .pipeline import BaizhiDetector
from .postprocess import filter_baizhi_fp
from .types import BaizhiBox, BaizhiDetectResult
from .video_stream import run_camera_loop

__all__ = [
    "BaizhiBox",
    "BaizhiDetectConfig",
    "BaizhiDetectResult",
    "BaizhiDetector",
    "filter_baizhi_fp",
    "resolve_default_weights",
    "run_camera_loop",
]
