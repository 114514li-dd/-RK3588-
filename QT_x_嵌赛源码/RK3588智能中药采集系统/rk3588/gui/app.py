#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中药材识别系统 GUI — 适配 RK3588 (PyQt6 + RKNN)。

用法 (板端):
    python3 rk3588/gui/app.py --camera /dev/video21
    bash rk3588/启动GUI.sh

用法 (PC 无 RKNN 时预览界面，检测不可用):
    python rk3588/gui/app.py --demo
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RK_DIR = ROOT / "rk3588"
GUI_DIR = Path(__file__).resolve().parent
for p in (str(RK_DIR), str(GUI_DIR), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
    from PyQt6.QtGui import QFont, QImage, QPixmap
    from PyQt6.QtWidgets import (
        QApplication,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSplitter,
        QTextEdit,
        QVBoxLayout,
        QWidget,
        QFileDialog,
    )
    _QT6 = True
except ImportError:
    try:
        from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
        from PyQt5.QtGui import QFont, QImage, QPixmap
        from PyQt5.QtWidgets import (
            QApplication,
            QFrame,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QSplitter,
            QTextEdit,
            QVBoxLayout,
            QWidget,
            QFileDialog,
        )
        _QT6 = False
    except ImportError as e:
        raise SystemExit(
            "缺少 PyQt。板端无外网时请:\n"
            "  1) bash rk3588/setup_gui_offline.sh\n"
            "  2) 或在 PC 下载 whl 后上传 offline_wheels/\n"
            "  3) 或先用: bash rk3588/启动枸杞检测.sh"
        ) from e


def _qt_align_center():
    return Qt.AlignmentFlag.AlignCenter if _QT6 else Qt.AlignCenter


def _qt_horizontal():
    return Qt.Orientation.Horizontal if _QT6 else Qt.Horizontal


def _qt_smooth():
    return Qt.TransformationMode.SmoothTransformation if _QT6 else Qt.SmoothTransformation


def _rgb888():
    return QImage.Format.Format_RGB888 if _QT6 else QImage.Format_RGB888


def _qt_align_right():
    return Qt.AlignmentFlag.AlignRight if _QT6 else Qt.AlignRight


def _frame_styled():
    return QFrame.Shape.StyledPanel if _QT6 else QFrame.StyledPanel


from chat_backend import HerbChatBackend
from herb_engine import FrameResult, HerbEngine, open_camera, resolve_camera


def bgr_to_qpixmap(frame: np.ndarray, max_w: int = 800) -> QPixmap:
    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    qimg = QImage(rgb.data, w, h, w * 3, _rgb888())
    pix = QPixmap.fromImage(qimg.copy())
    if w > max_w:
        pix = pix.scaledToWidth(max_w, _qt_smooth())
    return pix


class InferWorker(QThread):
    finished = pyqtSignal(object, float)

    def __init__(self, engine: HerbEngine):
        super().__init__()
        self.engine = engine
        self._frame: np.ndarray | None = None
        self._running = False

    def submit(self, frame: np.ndarray) -> None:
        if self._running:
            return
        self._frame = frame.copy()
        self.start()

    def run(self) -> None:
        if self._frame is None:
            return
        self._running = True
        t0 = time.perf_counter()
        try:
            result = self.engine.process_frame(self._frame)
        except Exception as e:
            result = FrameResult(vis=self._frame, status=f"推理错误: {e}")
        dt = time.perf_counter() - t0
        self.finished.emit(result, dt)
        self._running = False


class MainWindow(QMainWindow):
    def __init__(
        self,
        engine: HerbEngine | None,
        camera,
        demo: bool = False,
        cam_w: int = 640,
        cam_h: int = 480,
    ):
        super().__init__()
        self.engine = engine
        self.demo = demo
        self.camera_id = camera
        self.cam_w, self.cam_h = cam_w, cam_h
        self.cap: cv2.VideoCapture | None = None
        self.current_frame: np.ndarray | None = None
        self.last_result: FrameResult | None = None
        self.chat = HerbChatBackend()
        self.infer_worker = InferWorker(engine) if engine else None
        if self.infer_worker:
            self.infer_worker.finished.connect(self._on_infer_done)

        self.setWindowTitle("中药材识别系统")
        self.resize(1200, 720)
        self._fps_times: list[float] = []
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer)
        self.chat_log.append(self.chat.welcome)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        splitter = QSplitter(_qt_horizontal())
        root.addWidget(splitter)

        # —— 左侧：视频 + 按钮 + 检测日志 ——
        left = QWidget()
        left_layout = QVBoxLayout(left)

        title = QLabel("中药材识别系统")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #2e7d32;")
        left_layout.addWidget(title)

        self.video_label = QLabel("请打开摄像头或加载图片")
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setAlignment(_qt_align_center())
        self.video_label.setStyleSheet(
            "background:#111; color:#aaa; border:2px solid #4caf50;"
        )
        left_layout.addWidget(self.video_label, stretch=1)

        btn_row = QHBoxLayout()
        self.btn_cam = QPushButton("打开摄像头")
        self.btn_open = QPushButton("打开图片")
        self.btn_snap = QPushButton("拍照")
        self.btn_detect = QPushButton("检测")
        self.btn_save = QPushButton("保存结果")
        for b in (self.btn_cam, self.btn_open, self.btn_snap, self.btn_detect, self.btn_save):
            b.setStyleSheet(
                "QPushButton{background:#43a047;color:white;padding:8px 12px;border-radius:4px;}"
                "QPushButton:disabled{background:#888;}"
            )
            btn_row.addWidget(b)
        left_layout.addLayout(btn_row)

        self.btn_cam.clicked.connect(self.toggle_camera)
        self.btn_open.clicked.connect(self.open_image)
        self.btn_snap.clicked.connect(self.capture_photo)
        self.btn_detect.clicked.connect(self.run_detect)
        self.btn_save.clicked.connect(self.save_result)
        self.btn_save.setEnabled(False)

        log_title = QLabel("检测结果")
        log_title.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        left_layout.addWidget(log_title)
        self.detect_log = QTextEdit()
        self.detect_log.setReadOnly(True)
        self.detect_log.setMinimumHeight(160)
        left_layout.addWidget(self.detect_log)

        splitter.addWidget(left)

        # —— 右侧：AI 问答 ——
        right = QFrame()
        right.setFrameShape(_frame_styled())
        right_layout = QVBoxLayout(right)

        ai_header = QHBoxLayout()
        ai_title = QLabel("AI模型")
        ai_title.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        self.btn_ai = QPushButton("关闭AI模型")
        self.btn_ai.setCheckable(True)
        self.btn_ai.setChecked(True)
        self.btn_ai.setStyleSheet(
            "QPushButton{background:#e53935;color:white;padding:6px 10px;border-radius:4px;}"
            "QPushButton:checked{background:#43a047;}"
        )
        self.ai_status = QLabel("AI模型已开启")
        self.ai_status.setStyleSheet("color:#2e7d32;font-weight:bold;")
        ai_header.addWidget(ai_title)
        ai_header.addStretch()
        ai_header.addWidget(self.ai_status)
        ai_header.addWidget(self.btn_ai)
        right_layout.addLayout(ai_header)

        self.btn_ai.toggled.connect(self._toggle_ai)

        chat_title = QLabel("中药材知识问答")
        chat_title.setAlignment(_qt_align_center())
        chat_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        chat_title.setStyleSheet("background:#fafafa;padding:8px;border:1px solid #ddd;")
        right_layout.addWidget(chat_title)

        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        right_layout.addWidget(self.chat_log, stretch=1)

        input_row = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("例如：枸杞的性状是什么")
        self.chat_input.returnPressed.connect(self.send_chat)
        self.btn_send = QPushButton("发送")
        self.btn_send.clicked.connect(self.send_chat)
        input_row.addWidget(self.chat_input)
        input_row.addWidget(self.btn_send)
        right_layout.addLayout(input_row)

        self.fps_label = QLabel("FPS: —")
        self.fps_label.setAlignment(_qt_align_right())
        right_layout.addWidget(self.fps_label)

        splitter.addWidget(right)
        splitter.setSizes([780, 420])

    def _toggle_ai(self, checked: bool) -> None:
        self.chat.enabled = checked
        if checked:
            self.btn_ai.setText("关闭AI模型")
            self.ai_status.setText("AI模型已开启")
            self.ai_status.setStyleSheet("color:#2e7d32;font-weight:bold;")
        else:
            self.btn_ai.setText("开启AI模型")
            self.ai_status.setText("AI模型已关闭")
            self.ai_status.setStyleSheet("color:#888;font-weight:bold;")

    def toggle_camera(self) -> None:
        if self.cap and self.cap.isOpened():
            self._stop_camera()
            return
        self.cap = open_camera(self.camera_id)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "错误", f"无法打开摄像头 {self.camera_id}")
            self.cap = None
            return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cam_w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cam_h)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.btn_cam.setText("关闭摄像头")
        self._timer.start(33)

    def _stop_camera(self) -> None:
        self._timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.btn_cam.setText("打开摄像头")

    def _on_timer(self) -> None:
        if not self.cap:
            return
        ok, frame = self.cap.read()
        if not ok:
            return
        self.current_frame = frame
        if self.demo or not self.infer_worker:
            self._show_frame(frame)
        else:
            self.infer_worker.submit(frame)

    def _on_infer_done(self, result: FrameResult, dt: float) -> None:
        self.last_result = result
        self._show_frame(result.vis)
        self._fps_times.append(dt)
        if len(self._fps_times) > 30:
            self._fps_times.pop(0)
        fps = 1.0 / (sum(self._fps_times) / len(self._fps_times)) if self._fps_times else 0
        self.fps_label.setText(f"FPS: {fps:.1f}")
        if result.items:
            self._update_detect_log(result.items)
            self.btn_save.setEnabled(True)

    def _show_frame(self, frame: np.ndarray) -> None:
        self.video_label.setPixmap(bgr_to_qpixmap(frame))

    def open_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", str(ROOT), "Images (*.jpg *.jpeg *.png *.bmp)"
        )
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            QMessageBox.warning(self, "提示", "无法读取图片")
            return
        self._stop_camera()
        self.current_frame = img
        self.video_label.setPixmap(bgr_to_qpixmap(img))
        self.run_detect()

    def capture_photo(self) -> None:
        if self.current_frame is None:
            QMessageBox.information(self, "提示", "当前无画面")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存拍照", str(ROOT / "capture.jpg"), "JPEG (*.jpg)"
        )
        if path:
            cv2.imwrite(path, self.current_frame)
            QMessageBox.information(self, "完成", f"已保存: {path}")

    def run_detect(self) -> None:
        if self.demo:
            QMessageBox.information(
                self, "演示模式",
                "当前为 --demo 模式（无 RKNN）。请在 RK3588 板端运行以启用检测。",
            )
            return
        if self.current_frame is None:
            QMessageBox.information(self, "提示", "请先打开摄像头或图片")
            return
        if not self.infer_worker:
            return
        self.infer_worker.submit(self.current_frame)

    def _update_detect_log(self, items) -> None:
        blocks = []
        for it in items:
            blocks.append(
                self.chat.format_detection_entry(it.name, it.confidence, it.bbox)
            )
        self.detect_log.setPlainText("\n\n".join(blocks))

    def save_result(self) -> None:
        vis = self.last_result.vis if self.last_result else self.current_frame
        if vis is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存结果", str(ROOT / "result.jpg"), "JPEG (*.jpg)"
        )
        if path:
            cv2.imwrite(path, vis)
            QMessageBox.information(self, "完成", f"已保存: {path}")

    def send_chat(self) -> None:
        q = self.chat_input.text().strip()
        if not q:
            return
        self.chat_log.append(f"用户: {q}")
        herbs = [it.name for it in (self.last_result.items if self.last_result else [])]
        ans = self.chat.answer(q, context_herbs=herbs)
        self.chat_log.append(f"AI助手: {ans}\n")
        self.chat_input.clear()

    def closeEvent(self, event) -> None:
        self._stop_camera()
        if self.engine:
            self.engine.release()
        super().closeEvent(event)


def parse_args():
    p = argparse.ArgumentParser(description="中药材识别 GUI")
    p.add_argument("--herb", choices=["gouqi", "baizhi", "both"], default="both")
    p.add_argument("--cfg", default=str(RK_DIR / "deploy.yaml"))
    p.add_argument("--camera", default=None)
    p.add_argument("--demo", action="store_true", help="无 RKNN 时仅预览界面")
    return p.parse_args()


def main():
    args = parse_args()
    cfg_path = Path(args.cfg)
    import yaml

    cfg = yaml.safe_load(open(cfg_path, encoding="utf-8"))
    inf = cfg.get("inference", {})
    camera = resolve_camera(args.camera, inf.get("camera", 0))
    cam_w = int(inf.get("cam_width", 640))
    cam_h = int(inf.get("cam_height", 480))

    engine = None
    demo = args.demo
    if not demo:
        try:
            engine = HerbEngine(cfg_path, herb=args.herb)
            engine.load()
        except Exception as e:
            print(f"[警告] RKNN 未就绪，进入演示模式: {e}")
            demo = True

    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    win = MainWindow(engine, camera, demo=demo, cam_w=cam_w, cam_h=cam_h)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
