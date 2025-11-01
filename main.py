import sys
import cv2
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout,
    QLabel, QTextEdit, QFileDialog, QHBoxLayout, QLineEdit, QSpinBox
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt


def focus_measure(gray):
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    return (gx**2 + gy**2).sum()


class MoonSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("最清晰帧选择器 (PySide6)")
        self.resize(900, 600)

        self.video_path = None
        self.frames = []
        self.scores = []
        self.current_idx = -1

        # 控件
        self.load_btn = QPushButton("加载视频")
        self.calc_btn = QPushButton("计算清晰度")
        self.show_btn = QPushButton("显示选定帧")
        self.save_btn = QPushButton("保存帧")

        self.interval_label = QLabel("抽样间隔(帧)：")
        self.interval_box = QSpinBox()
        self.interval_box.setRange(1, 500)
        self.interval_box.setValue(5)

        self.info_label = QLabel("帧号输入：")
        self.index_edit = QLineEdit()

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.image_label = QLabel(alignment=Qt.AlignCenter)
        self.image_label.setText("未加载视频")

        # 布局
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.load_btn)
        top_layout.addWidget(self.calc_btn)
        top_layout.addWidget(self.interval_label)
        top_layout.addWidget(self.interval_box)
        top_layout.addWidget(self.info_label)
        top_layout.addWidget(self.index_edit)
        top_layout.addWidget(self.show_btn)
        top_layout.addWidget(self.save_btn)

        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addWidget(self.text_edit, 2)
        layout.addWidget(self.image_label, 5)
        self.setLayout(layout)

        # 信号连接
        self.load_btn.clicked.connect(self.load_video)
        self.calc_btn.clicked.connect(self.compute_scores)
        self.show_btn.clicked.connect(self.show_frame)
        self.save_btn.clicked.connect(self.save_frame)

        self.apply_style()

    def apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #f6f7fb;
                font-family: "Microsoft YaHei";
                font-size: 14px;
                color: #2c2c2c;
            }
            QPushButton {
                background-color: #4b8bf5;
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6ea1f8;
            }
            QPushButton:pressed {
                background-color: #3a6ed9;
            }
            QTextEdit, QLineEdit, QSpinBox {
                background-color: #ffffff;
                border: 1px solid #c9c9c9;
                border-radius: 6px;
                padding: 6px;
            }
            QLabel {
                font-weight: bold;
            }
        """)

    def load_video(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择视频", "", "Video Files (*.mp4 *.avi *.mov)")
        if not file:
            return
        self.video_path = file
        self.frames.clear()
        self.scores.clear()
        self.text_edit.setPlainText(f"已加载视频：{file}\n")

    def compute_scores(self):
        if not self.video_path:
            self.text_edit.append("请先加载视频。")
            return

        interval = self.interval_box.value()

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.text_edit.append("无法打开视频。")
            return

        self.text_edit.append(f"正在计算（每隔 {interval} 帧抽样）...\n")
        QApplication.processEvents()

        idx = 0
        self.frames.clear()
        self.scores.clear()

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if idx % interval == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                h, w = gray.shape
                roi = gray[h//4:h*3//4, w//4:w*3//4]
                score = focus_measure(roi)

                self.frames.append(frame)
                self.scores.append(score)
                self.text_edit.append(f"帧 {idx}: 清晰度 {score:.2f}")
                QApplication.processEvents()

            idx += 1

        cap.release()

        if not self.scores:
            self.text_edit.append("没有成功计算任何帧。")
            return

        max_score = max(self.scores)
        best_idx = self.scores.index(max_score)
        frame_no = best_idx * interval  # 显示原始视频帧号
        self.text_edit.append(f"\n计算完成。推荐最清晰帧号约为：{frame_no}（清晰度 {max_score:.2f}）")
        self.text_edit.append("你可在上方输入帧号（抽样索引）手动查看。")

    def show_frame(self):
        if not self.frames:
            self.text_edit.append("还没有计算或加载视频。")
            return
        try:
            idx = int(self.index_edit.text())
        except ValueError:
            self.text_edit.append("请输入有效的帧号（抽样索引）。")
            return
        if idx < 0 or idx >= len(self.frames):
            self.text_edit.append("帧号超出范围。")
            return

        frame = self.frames[idx]
        self.current_idx = idx
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg).scaled(600, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(pix)
        self.text_edit.append(f"显示第 {idx} 个抽样帧，清晰度 {self.scores[idx]:.2f}")

    def save_frame(self):
        if self.current_idx < 0:
            self.text_edit.append("请先显示要保存的帧。")
            return
        save_path = f"selected_frame_{self.current_idx}.jpg"
        cv2.imwrite(save_path, self.frames[self.current_idx])
        self.text_edit.append(f"已保存为 {save_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MoonSelector()
    w.show()
    sys.exit(app.exec())
