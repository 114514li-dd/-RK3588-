"""YOLOv8 RKNN 后处理 — Ultralytics 单输出 + 飞凌多分支双格式。"""

from __future__ import annotations

import numpy as np

IMG_SIZE = 640


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -50, 50)))


def _maybe_sigmoid(scores: np.ndarray) -> np.ndarray:
    if scores.size == 0:
        return scores
    if scores.max() > 1.0 or scores.min() < 0.0:
        return _sigmoid(scores)
    return scores


def _xywh2xyxy(x: np.ndarray) -> np.ndarray:
    y = np.empty_like(x)
    y[:, 0] = x[:, 0] - x[:, 2] / 2
    y[:, 1] = x[:, 1] - x[:, 3] / 2
    y[:, 2] = x[:, 0] + x[:, 2] / 2
    y[:, 3] = x[:, 1] + x[:, 3] / 2
    return y


def nms_boxes(boxes: np.ndarray, scores: np.ndarray, iou_thresh: float = 0.45) -> np.ndarray:
    x1, y1, x2, y2 = boxes.T
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        order = order[1:][iou <= iou_thresh]
    return np.array(keep, dtype=int)


def scale_boxes(
    boxes: np.ndarray,
    img_shape: tuple[int, int],
    input_size: int = IMG_SIZE,
    ratio_pad: tuple | None = None,
) -> np.ndarray:
    """将 letterbox(640) 坐标映射回原图 — 对齐 Ultralytics ops.scale_boxes。"""
    if len(boxes) == 0:
        return boxes
    h, w = img_shape
    boxes = boxes.copy().astype(np.float32)
    if ratio_pad is None:
        gain = min(input_size / h, input_size / w)
        pad_x = round((input_size - round(w * gain)) / 2 - 0.1)
        pad_y = round((input_size - round(h * gain)) / 2 - 0.1)
    else:
        gain = float(ratio_pad[0][0])
        pad_x, pad_y = ratio_pad[1]
    boxes[:, [0, 2]] -= pad_x
    boxes[:, [1, 3]] -= pad_y
    boxes[:, :4] /= gain
    boxes[:, 0::2] = boxes[:, 0::2].clip(0, w)
    boxes[:, 1::2] = boxes[:, 1::2].clip(0, h)
    return boxes


def filter_by_area(
    boxes: np.ndarray,
    scores: np.ndarray,
    img_shape: tuple[int, int],
    min_ratio: float = 0.0,
    max_ratio: float = 0.0,
    large_area: float = 0.82,
    large_conf: float = 0.82,
) -> tuple[np.ndarray, np.ndarray]:
    if len(boxes) == 0:
        return boxes, scores
    h, w = img_shape
    keep = []
    for i, box in enumerate(boxes):
        conf = float(scores[i])
        r = (box[2] - box[0]) * (box[3] - box[1]) / (h * w)
        if min_ratio > 0 and r < min_ratio:
            continue
        if max_ratio > 0 and r > max_ratio:
            continue
        if r > large_area and conf < large_conf:
            continue
        keep.append(i)
    if not keep:
        return np.zeros((0, 4)), np.zeros((0,))
    idx = np.array(keep, dtype=int)
    return boxes[idx], scores[idx]


def _dfl(position: np.ndarray) -> np.ndarray:
    n, c, h, w = position.shape
    p_num = 4
    mc = c // p_num
    y = position.reshape(n, p_num, mc, h, w)
    e_y = np.exp(y - np.max(y, axis=2, keepdims=True))
    y = e_y / np.sum(e_y, axis=2, keepdims=True)
    acc = np.arange(mc).reshape(1, 1, mc, 1, 1)
    return (y * acc).sum(2)


def _box_process(position: np.ndarray, input_size: int = IMG_SIZE) -> np.ndarray:
    grid_h, grid_w = position.shape[2:4]
    col, row = np.meshgrid(np.arange(grid_w), np.arange(grid_h))
    col = col.reshape(1, 1, grid_h, grid_w)
    row = row.reshape(1, 1, grid_h, grid_w)
    grid = np.concatenate((col, row), axis=1)
    stride = np.array([input_size // grid_h, input_size // grid_w]).reshape(1, 2, 1, 1)
    position = _dfl(position)
    box_xy = grid + 0.5 - position[:, 0:2, :, :]
    box_xy2 = grid + 0.5 + position[:, 2:4, :, :]
    return np.concatenate((box_xy * stride, box_xy2 * stride), axis=1)


def _sp_flatten(x: np.ndarray) -> np.ndarray:
    ch = x.shape[1]
    return x.transpose(0, 2, 3, 1).reshape(-1, ch)


def _is_multi_branch(outputs: list[np.ndarray], nc: int = 1) -> bool:
    if len(outputs) < 3:
        return False
    o0 = outputs[0]
    if o0.ndim != 4:
        return False
    # Ultralytics 单输出 [1,4+nc,N] 不应走多分支
    if len(outputs) == 1:
        return False
    return o0.shape[1] >= 16 and o0.shape[1] != 4 + nc


def _is_single_tensor(outputs: list[np.ndarray], nc: int = 1) -> bool:
    if len(outputs) != 1:
        return False
    o = outputs[0]
    if o.ndim != 3:
        return False
    ch = o.shape[1]
    if ch == 4 + nc:
        return True
    if o.shape[2] == 4 + nc:
        return True
    return False


def _boxes_to_xyxy(boxes4: np.ndarray) -> np.ndarray:
    """自动识别 xywh / xyxy（RKNN 导出格式不一致）。"""
    if len(boxes4) == 0:
        return boxes4
    as_xywh = _xywh2xyxy(boxes4.astype(np.float32))
    wh_ok = (as_xywh[:, 2] > as_xywh[:, 0]) & (as_xywh[:, 3] > as_xywh[:, 1])
    if wh_ok.mean() >= 0.5:
        return as_xywh
    as_xyxy = boxes4.astype(np.float32)
    xy_ok = (as_xyxy[:, 2] > as_xyxy[:, 0]) & (as_xyxy[:, 3] > as_xyxy[:, 1])
    if xy_ok.mean() >= 0.5:
        return as_xyxy
    return as_xywh


def _valid_boxes(boxes: np.ndarray, scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if len(boxes) == 0:
        return boxes, scores
    ok = (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1])
    ok &= (boxes[:, 2] - boxes[:, 0] >= 2) & (boxes[:, 3] - boxes[:, 1] >= 2)
    if not ok.any():
        return np.zeros((0, 4)), np.zeros((0,))
    return boxes[ok], scores[ok]


def _normalize_box_scale(boxes_xywh: np.ndarray, input_size: int) -> np.ndarray:
    """若坐标在 0~1 范围，按输入尺寸放大到 letterbox 像素坐标。"""
    if len(boxes_xywh) == 0:
        return boxes_xywh
    peak = float(np.max(np.abs(boxes_xywh)))
    if peak <= 1.5:
        boxes_xywh = boxes_xywh * input_size
    return boxes_xywh


def _prepare_single_pred(pred: np.ndarray, nc: int) -> np.ndarray:
    if pred.ndim == 3:
        pred = pred[0]
    if pred.shape[0] == 4 + nc:
        pred = pred.T
    elif pred.shape[-1] != 4 + nc:
        pred = pred.T
    return pred.astype(np.float32)


def _postprocess_multi_branch(
    outputs: list[np.ndarray],
    conf_thres: float,
    iou_thres: float,
    max_det: int,
    input_size: int = IMG_SIZE,
) -> tuple[np.ndarray, np.ndarray]:
    n_branch = 3
    pair = max(len(outputs) // n_branch, 1)

    boxes_list, cls_list = [], []
    for i in range(n_branch):
        bi = pair * i
        ci = bi + 1
        if ci >= len(outputs):
            break
        boxes_list.append(_box_process(outputs[bi], input_size))
        cls_list.append(outputs[ci])

    if not boxes_list:
        return np.zeros((0, 4)), np.zeros((0,))

    boxes = np.concatenate([_sp_flatten(b) for b in boxes_list], axis=0)
    cls_conf = np.concatenate([_sp_flatten(c) for c in cls_list], axis=0)
    scores = cls_conf.reshape(-1) if cls_conf.shape[1] == 1 else cls_conf.max(axis=1)
    scores = _sigmoid(scores.astype(np.float32))

    mask = scores >= conf_thres
    boxes, scores = boxes[mask], scores[mask]
    if len(scores) == 0:
        return np.zeros((0, 4)), np.zeros((0,))

    keep = nms_boxes(boxes, scores, iou_thres)[:max_det]
    boxes, scores = boxes[keep], scores[keep]
    return _valid_boxes(boxes, scores)


def _postprocess_single_tensor(
    pred: np.ndarray,
    conf_thres: float,
    iou_thres: float,
    nc: int,
    max_det: int,
    input_size: int = IMG_SIZE,
) -> tuple[np.ndarray, np.ndarray]:
    """Ultralytics RKNN 常见格式 [1,4+nc,N] 或 [1,N,4+nc]。"""
    pred = _prepare_single_pred(pred, nc)
    boxes_xywh = pred[:, :4].astype(np.float32)
    boxes_xywh = _normalize_box_scale(boxes_xywh, input_size)
    if nc == 1:
        scores = _maybe_sigmoid(pred[:, 4].astype(np.float32))
    else:
        scores = _maybe_sigmoid(pred[:, 4 : 4 + nc].max(axis=1).astype(np.float32))

    mask = scores >= conf_thres
    boxes_xywh, scores = boxes_xywh[mask], scores[mask]
    if len(scores) == 0:
        return np.zeros((0, 4)), np.zeros((0,))

    boxes = _boxes_to_xyxy(boxes_xywh)
    keep = nms_boxes(boxes, scores, iou_thres)[:max_det]
    boxes, scores = boxes[keep], scores[keep]
    return _valid_boxes(boxes, scores)


def describe_outputs(outputs: list[np.ndarray]) -> str:
    parts = []
    for i, o in enumerate(outputs):
        parts.append(f"out{i}={getattr(o, 'shape', type(o))} dtype={getattr(o, 'dtype', '?')}")
    return " | ".join(parts)


def detect_postprocess_mode(outputs: list[np.ndarray], nc: int = 1) -> str:
    if _is_single_tensor(outputs, nc):
        return "single"
    if _is_multi_branch(outputs, nc):
        return "multi"
    o0 = outputs[0] if outputs else None
    if o0 is not None and o0.ndim == 3 and (o0.shape[1] == 4 + nc or o0.shape[2] == 4 + nc):
        return "single"
    return "multi"


def output_tensor_peak(outputs: list[np.ndarray], nc: int = 1) -> float:
    """直接从 RKNN 输出张量取分类峰值（不经过 NMS），用于判断模型是否随画面变化。"""
    if not outputs:
        return 0.0
    if _is_single_tensor(outputs, nc) or (
        outputs[0].ndim == 3 and (outputs[0].shape[1] == 4 + nc or outputs[0].shape[2] == 4 + nc)
    ):
        pred = _prepare_single_pred(np.asarray(outputs[0], dtype=np.float32), nc)
        scores = pred[:, 4] if nc == 1 else pred[:, 4 : 4 + nc].max(axis=1)
        return float(_maybe_sigmoid(scores.astype(np.float32)).max())
    if _is_multi_branch(outputs, nc):
        pair = max(len(outputs) // 3, 1)
        peaks = []
        for i in range(3):
            ci = pair * i + 1
            if ci >= len(outputs):
                break
            cls = np.asarray(outputs[ci], dtype=np.float32)
            flat = _sp_flatten(cls) if cls.ndim == 4 else cls.reshape(-1, cls.shape[-1])
            s = flat.reshape(-1) if flat.shape[1] == 1 else flat.max(axis=1)
            peaks.append(float(_sigmoid(s).max()))
        return max(peaks) if peaks else 0.0
    return float(np.max(outputs[0]))


def postprocess_yolov8(
    outputs: list[np.ndarray],
    conf_thres: float = 0.01,
    iou_thres: float = 0.45,
    nc: int = 1,
    max_det: int = 10,
    input_size: int = IMG_SIZE,
) -> tuple[np.ndarray, np.ndarray]:
    if not outputs:
        return np.zeros((0, 4)), np.zeros((0,))

    mode = detect_postprocess_mode(outputs, nc)
    if mode == "single":
        return _postprocess_single_tensor(outputs[0], conf_thres, iou_thres, nc, max_det, input_size)

    return _postprocess_multi_branch(outputs, conf_thres, iou_thres, max_det, input_size)
