"""白芷检测结果数据结构 — 兼容下游计数、框选、保存等业务逻辑。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class BaizhiBox:
    """单个白芷检测框（像素坐标，左上-右下）。"""

    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    class_id: int = 0
    class_name: str = "白芷"

    @property
    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    @property
    def height(self) -> int:
        return max(0, self.y2 - self.y1)

    @property
    def area(self) -> int:
        return self.width * self.height

    def bbox_xywh(self) -> tuple[int, int, int, int]:
        """Qt QRect 兼容格式: (x, y, width, height)。"""
        return self.x1, self.y1, self.width, self.height

    def bbox_xyxy(self) -> tuple[int, int, int, int]:
        return self.x1, self.y1, self.x2, self.y2

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.class_name,
            "class_id": self.class_id,
            "confidence": round(self.confidence, 4),
            "bbox_xyxy": [self.x1, self.y1, self.x2, self.y2],
            "bbox_xywh": list(self.bbox_xywh()),
        }


@dataclass
class BaizhiDetectResult:
    """一帧/一张图的完整检测结果。"""

    success: bool
    count: int
    boxes: list[BaizhiBox] = field(default_factory=list)
    image_width: int = 0
    image_height: int = 0
    error_message: str = ""

    @property
    def items(self) -> list[BaizhiBox]:
        return self.boxes

    def best(self) -> BaizhiBox | None:
        if not self.boxes:
            return None
        return max(self.boxes, key=lambda b: b.confidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "count": self.count,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "error_message": self.error_message,
            "items": [b.to_dict() for b in self.boxes],
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def failure(cls, message: str) -> BaizhiDetectResult:
        return cls(success=False, count=0, error_message=message)
