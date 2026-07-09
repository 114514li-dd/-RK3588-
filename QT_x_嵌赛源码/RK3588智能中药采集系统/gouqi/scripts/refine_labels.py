#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将枸杞整图标注缩小为 0.82 中心框，提高检测置信度。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LBL_DIRS = [
    ROOT / "gouqi/dataset/labels/train",
    ROOT / "gouqi/dataset/labels/val",
]
NEW_LINE = "0 0.5 0.5 0.82 0.82\n"


def main() -> None:
    n = 0
    for d in LBL_DIRS:
        for lbl in d.glob("gouqi*.txt"):
            if lbl.stem.startswith("neg_"):
                continue
            text = lbl.read_text(encoding="utf-8").strip()
            if not text:
                continue
            lbl.write_text(NEW_LINE, encoding="utf-8")
            n += 1
    for cache in (ROOT / "gouqi/dataset/labels/train.cache", ROOT / "gouqi/dataset/labels/val.cache"):
        if cache.exists():
            cache.unlink()
    print(f"已精修 {n} 个枸杞标注 -> 中心框 0.82")


if __name__ == "__main__":
    main()
