"""YOLOv8 输出解析、置信度过滤、NMS 后业务过滤。"""

from __future__ import annotations

import numpy as np

from .config import BaizhiDetectConfig
from .types import BaizhiBox, BaizhiDetectResult


def _area_ratio(box: np.ndarray, frame_shape: tuple[int, int]) -> float:
    h, w = frame_shape[:2]
    x1, y1, x2, y2 = box
    return float((x2 - x1) * (y2 - y1)) / max(h * w, 1)


def filter_boxes_numpy(
    xyxy: np.ndarray,
    confs: np.ndarray,
    frame_shape: tuple[int, int],
    cfg: BaizhiDetectConfig,
) -> tuple[np.ndarray, np.ndarray] | None:
    """置信度 + 面积过滤，去除过小误检与「几乎整图但置信不足」的大框。"""
    if len(xyxy) == 0:
        return None

    keep_xy, keep_cf = [], []
    for box, conf in zip(xyxy, confs):
        if conf < cfg.conf:
            continue
        ratio = _area_ratio(box, frame_shape)
        if cfg.min_area_ratio > 0 and ratio < cfg.min_area_ratio:
            continue
        if cfg.max_area_ratio > 0 and ratio > cfg.max_area_ratio:
            continue
        if ratio > cfg.large_area_ratio and conf < cfg.large_area_min_conf:
            continue
        keep_xy.append(box)
        keep_cf.append(conf)

    if not keep_xy:
        return None
    return np.array(keep_xy, dtype=np.float32), np.array(keep_cf, dtype=np.float32)


def parse_ultralytics_result(
    result,
    cfg: BaizhiDetectConfig,
    image_bgr: np.ndarray | None = None,
) -> BaizhiDetectResult:
    """将 ultralytics Results 解析为 BaizhiDetectResult。"""
    if image_bgr is not None:
        h, w = image_bgr.shape[:2]
    elif result.orig_img is not None:
        h, w = result.orig_img.shape[:2]
    else:
        return BaizhiDetectResult.failure("无法获取图像尺寸")

    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return BaizhiDetectResult(
            success=True,
            count=0,
            boxes=[],
            image_width=w,
            image_height=h,
        )

    xyxy = boxes.xyxy.cpu().numpy()
    confs = boxes.conf.cpu().numpy()
    cls_ids = boxes.cls.cpu().numpy().astype(int) if boxes.cls is not None else np.zeros(len(confs), dtype=int)

    filtered = filter_boxes_numpy(xyxy, confs, (h, w), cfg)
    if filtered is None:
        return BaizhiDetectResult(success=True, count=0, boxes=[], image_width=w, image_height=h)

    xyxy_f, confs_f = filtered
    order = np.argsort(-confs_f)
    items: list[BaizhiBox] = []
    for idx in order:
        x1, y1, x2, y2 = xyxy_f[idx]
        cid = int(cls_ids[idx]) if idx < len(cls_ids) else 0
        items.append(
            BaizhiBox(
                x1=int(round(x1)),
                y1=int(round(y1)),
                x2=int(round(x2)),
                y2=int(round(y2)),
                confidence=float(confs_f[idx]),
                class_id=cid,
                class_name=cfg.class_name,
            )
        )

    return BaizhiDetectResult(
        success=True,
        count=len(items),
        boxes=items,
        image_width=w,
        image_height=h,
    )


def apply_nms_numpy(
    xyxy: np.ndarray,
    confs: np.ndarray,
    iou_thresh: float = 0.45,
    max_det: int = 20,
) -> tuple[np.ndarray, np.ndarray]:
    """对已有框再做一次 NMS（处理重叠白芷）。"""
    if len(xyxy) == 0:
        return xyxy, confs

    x1, y1, x2, y2 = xyxy.T
    areas = (x2 - x1) * (y2 - y1)
    order = confs.argsort()[::-1]
    keep: list[int] = []
    while order.size and len(keep) < max_det:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        order = order[1:][iou <= iou_thresh]
    keep_arr = np.array(keep, dtype=int)
    return xyxy[keep_arr], confs[keep_arr]


def filter_baizhi_fp(
    xyxy: np.ndarray,
    confs: np.ndarray,
    frame_shape: tuple[int, int],
    conf_min: float,
    *,
    min_area: float = 0.02,
    large_area: float = 0.82,
    large_conf: float = 0.82,
) -> tuple[np.ndarray, np.ndarray] | None:
    """herbs2 双类检测用的白芷框过滤（兼容旧 API）。"""
    cfg = BaizhiDetectConfig(
        conf=conf_min,
        min_area_ratio=min_area,
        large_area_ratio=large_area,
        large_area_min_conf=large_conf,
    )
    return filter_boxes_numpy(xyxy, confs, frame_shape, cfg)
