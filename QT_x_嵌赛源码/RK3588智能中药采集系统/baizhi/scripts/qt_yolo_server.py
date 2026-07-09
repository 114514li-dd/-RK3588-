#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Qt YOLOv8 推理桥接服务 — 通过 stdin/stdout 行分隔 JSON 与 C++ Qt 通信。

协议（每行一条 JSON 请求，stdout 每行一条 JSON 响应）:
    {"cmd":"init","weights":"...","conf":0.55,"device":""}
    {"cmd":"detect_path","path":"C:/test.jpg"}
    {"cmd":"detect_b64","data":"<base64 jpeg>"}
    {"cmd":"quit"}

运行:
    python baizhi/scripts/qt_yolo_server.py
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baizhi.detection import BaizhiDetectConfig, BaizhiDetector, resolve_default_weights


def _reply(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main() -> None:
    cfg = BaizhiDetectConfig()
    detector: BaizhiDetector | None = None

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
            cmd = req.get("cmd", "")

            if cmd == "init":
                if req.get("weights"):
                    cfg.weights = req["weights"]
                else:
                    cfg.weights = resolve_default_weights()
                if "conf" in req:
                    cfg.conf = float(req["conf"])
                if "iou" in req:
                    cfg.iou = float(req["iou"])
                if "device" in req:
                    cfg.device = str(req["device"])
                if "imgsz" in req:
                    cfg.imgsz = int(req["imgsz"])
                detector = BaizhiDetector(cfg)
                _reply({"ok": True, "cmd": "init", "weights": cfg.weights})

            elif cmd == "detect_path":
                if detector is None:
                    detector = BaizhiDetector(cfg)
                path = req.get("path", "")
                result = detector.detect_image(path)
                resp = result.to_dict()
                resp["ok"] = result.success
                resp["cmd"] = "detect_path"
                _reply(resp)

            elif cmd == "detect_b64":
                if detector is None:
                    detector = BaizhiDetector(cfg)
                data = req.get("data", "")
                if not data:
                    _reply({"ok": False, "cmd": "detect_b64", "error_message": "missing data"})
                    continue
                buf = np.frombuffer(base64.b64decode(data), dtype=np.uint8)
                img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
                if img is None:
                    _reply({"ok": False, "cmd": "detect_b64", "error_message": "imdecode failed"})
                    continue
                result = detector.detect_frame(img)
                resp = result.to_dict()
                resp["ok"] = result.success
                resp["cmd"] = "detect_b64"
                _reply(resp)

            elif cmd == "ping":
                _reply({"ok": True, "cmd": "ping"})

            elif cmd == "quit":
                _reply({"ok": True, "cmd": "quit"})
                break

            else:
                _reply({"ok": False, "error_message": f"unknown cmd: {cmd}"})

        except Exception as exc:
            _reply({"ok": False, "error_message": str(exc)})


if __name__ == "__main__":
    main()
