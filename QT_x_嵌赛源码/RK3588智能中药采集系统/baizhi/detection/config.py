"""白芷 YOLOv8 检测默认配置。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_default_weights() -> str:
    """按版本优先级查找已训练权重（v7 最新）。"""
    root = _repo_root()
    for name in (
        "baizhi_yolov8s_ca_v7",
        "baizhi_yolov8s_ca_v6",
        "baizhi_yolov8s_ca_v5",
        "baizhi_yolov8s_ca_v4",
        "baizhi_yolov8s_ca_v3",
        "baizhi_yolov8s_ca_v2",
        "baizhi_yolov8s_ca",
    ):
        path = root / f"baizhi/runs/detect/{name}/weights/best.pt"
        if path.exists():
            return str(path)
    return str(root / "baizhi/runs/detect/baizhi_yolov8s_ca/weights/best.pt")


@dataclass
class BaizhiDetectConfig:
    """推理与后处理参数。"""

    weights: str = field(default_factory=resolve_default_weights)
    conf: float = 0.55
    iou: float = 0.45
    imgsz: int = 640
    device: str = ""
    max_det: int = 20
    class_name: str = "白芷"

    # OpenCV 预处理（仅增强画质，不做传统阈值/轮廓检测）
    enhance_contrast: bool = False
    clahe_clip: float = 2.0

    # 后处理：置信度 + 面积过滤（解决模糊/重叠误检）
    min_area_ratio: float = 0.015
    max_area_ratio: float = 0.0
    large_area_ratio: float = 0.82
    large_area_min_conf: float = 0.82

    # 可视化
    box_shrink: float = 0.65
    draw_labels: bool = True

    # 视频流优化
    infer_every: int = 2
    max_fps: float = 10.0
    confirm_frames: int = 2
    hold_ms: int = 0

    @classmethod
    def balanced(cls, **kwargs) -> BaizhiDetectConfig:
        """优先检出：略低置信度 + 连续帧确认。"""
        cfg = cls(conf=0.50, min_area_ratio=0.02, confirm_frames=2)
        for k, v in kwargs.items():
            setattr(cfg, k, v)
        return cfg

    @classmethod
    def strict(cls, **kwargs) -> BaizhiDetectConfig:
        """优先抗误检：高置信度 + 大框过滤。"""
        cfg = cls(
            conf=0.75,
            min_area_ratio=0.02,
            max_area_ratio=0.85,
            confirm_frames=3,
        )
        for k, v in kwargs.items():
            setattr(cfg, k, v)
        return cfg
