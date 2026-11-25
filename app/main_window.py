from __future__ import annotations

from pathlib import Path
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QComboBox, QSpinBox,
    QDoubleSpinBox, QSlider, QProgressBar, QFileDialog, QMessageBox,
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QScrollArea
)

from core.generator import GeneratorSettings, generate_heightmap
from core.normal_math import height_to_normal
from export.exporter import save_normal_map


class GenerationWorker(QObject):
    finished = Signal(object)
    progress = Signal(int)
    failed = Signal(str)

    def __init__(self, settings: GeneratorSettings, convention: str):
        super().__init__()
        self.settings = settings
        self.convention = convention

    def run(self):
        try:
            height = generate_heightmap(self.settings, self.progress.emit)
            result = height_to_normal(height, strength=5.0, y_convention=self.convention,
                                      seamless=self.settings.seamless)
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AquaForge — Water Normal Map Generator")
        self.resize(1280, 820)
        self.current_image: np.ndarray | None = None
        self.thread: QThread | None = None
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        layout = QHBoxLayout(root)
        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls = QWidget()
        panel = QVBoxLayout(controls)

        title = QLabel("AquaForge")
        title.setStyleSheet("font-size: 22pt; font-weight: 700;")
        subtitle = QLabel("Water surface normal map generator")
        subtitle.setStyleSheet("color: #9ba5b3;")
        panel.addWidget(title)
        panel.addWidget(subtitle)

        resolution = QGroupBox("Output")
        form = QFormLayout(resolution)
        self.width_box = QComboBox()
        self.width_box.addItems(["256", "512", "1024", "2048", "4096"])
        self.width_box.setCurrentText("1024")
        self.height_box = QComboBox()
        self.height_box.addItems(["256", "512", "1024", "2048", "4096"])
        self.height_box.setCurrentText("1024")
        form.addRow("Width", self.width_box)
        form.addRow("Height", self.height_box)
        self.convention = QComboBox()
        self.convention.addItems(["OpenGL (Y+)", "DirectX (Y−)"])
        form.addRow("Normal format", self.convention)
        panel.addWidget(resolution)

        waves = QGroupBox("Procedural waves")
        wf = QFormLayout(waves)
        self.wave_scale = self._double(4.0, 0.5, 40, 0.5)
        self.wave_strength = self._double(1.0, 0.05, 4, 0.05)
        self.frequency = self._double(1.0, 0.1, 5, 0.1)
        self.direction = self._double(35, 0, 360, 1)
        self.wind = self._double(0.35, 0, 2, 0.05)
        self.ripple = self._double(0.25, 0, 2, 0.05)
        self.ripple_scale = self._double(18, 2, 80, 1)
        self.detail = QSpinBox()
        self.detail.setRange(1, 12)
        self.detail.setValue(3)
        self.distortion = self._double(0.15, 0, 1, 0.01)
        for label, widget in [
            ("Wave scale", self.wave_scale), ("Wave strength", self.wave_strength),
            ("Frequency", self.frequency), ("Direction (°)", self.direction),
            ("Wind strength", self.wind), ("Ripple intensity", self.ripple),
            ("Ripple scale", self.ripple_scale), ("Detail level", self.detail),
            ("Distortion", self.distortion)
        ]:
            wf.addRow(label, widget)
        panel.addWidget(waves)

        self.seamless = QPushButton("Seamless mode: ON")
        self.seamless.setCheckable(True)
        self.seamless.setChecked(True)
        self.seamless.clicked.connect(lambda checked: self.seamless.setText(
            "Seamless mode: ON" if checked else "Seamless mode: OFF"))
        panel.addWidget(self.seamless)

        actions = QGroupBox("Actions")
        af = QVBoxLayout(actions)
        self.generate_button = QPushButton("Generate Normal Map")
        self.generate_button.setDefault(True)
        self.generate_button.clicked.connect(self.generate)
        self.random_button = QPushButton("Randomize Seed")
        self.random_button.clicked.connect(self.randomize_seed)
        self.export_button = QPushButton("Export texture…")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export)
        af.addWidget(self.generate_button)
        af.addWidget(self.random_button)
        af.addWidget(self.export_button)
        panel.addWidget(actions)
        panel.addStretch(1)
        controls_scroll.setWidget(controls)
        controls_scroll.setMinimumWidth(330)
        layout.addWidget(controls_scroll, 0)

        preview_panel = QVBoxLayout()
        preview_header = QHBoxLayout()
        preview_header.addWidget(QLabel("2D NORMAL MAP PREVIEW"))
        preview_header.addStretch(1)
        self.info = QLabel("No texture generated")
        preview_header.addWidget(self.info)
        preview_panel.addLayout(preview_header)
        self.preview = QLabel("Click Generate to create your first water normal map")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(500, 500)
        self.preview.setStyleSheet("background: #15181d; border: 1px solid #3b414b; border-radius: 6px; color: #87919e;")
        preview_panel.addWidget(self.preview, 1)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.status = QLabel("Ready")
        preview_panel.addWidget(self.progress)
        preview_panel.addWidget(self.status)
        layout.addLayout(preview_panel, 1)
        self.setCentralWidget(root)

    @staticmethod
    def _double(value: float, minimum: float, maximum: float, step: float) -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setRange(minimum, maximum)
        box.setSingleStep(step)
        box.setValue(value)
        box.setDecimals(2)
        return box

    def _settings(self) -> GeneratorSettings:
        return GeneratorSettings(
            width=int(self.width_box.currentText()), height=int(self.height_box.currentText()),
            wave_scale=self.wave_scale.value(), wave_strength=self.wave_strength.value(),
            frequency=self.frequency.value(), direction=self.direction.value(),
            wind_strength=self.wind.value(), ripple_intensity=self.ripple.value(),
            ripple_scale=self.ripple_scale.value(), detail=self.detail.value(),
            distortion=self.distortion.value(), seed=getattr(self, "seed", 12345),
            seamless=self.seamless.isChecked()
        )

    def generate(self):
        if self.thread and self.thread.isRunning():
            return
        self.generate_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.progress.setValue(0)
        self.status.setText("Generating on CPU…")
        self.thread = QThread(self)
        self.worker = GenerationWorker(self._settings(), "OpenGL" if self.convention.currentIndex() == 0 else "DirectX")
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self._on_generated)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self._thread_finished)
        self.thread.start()

    def _on_generated(self, image: np.ndarray):
        self.current_image = image
        h, w, _ = image.shape
        qimage = QImage(image.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qimage)
        self.preview.setPixmap(pixmap.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation))
        self.info.setText(f"{w} × {h} px")
        self.status.setText("Generation complete")
        self.export_button.setEnabled(True)

    def _on_failed(self, message: str):
        self.status.setText("Generation failed")
        QMessageBox.critical(self, "Generation error", message)

    def _thread_finished(self):
        self.generate_button.setEnabled(True)
        self.thread = None

    def randomize_seed(self):
        import secrets
        self.seed = secrets.randbelow(2**31)
        self.status.setText(f"Seed: {self.seed}")

    def export(self):
        if self.current_image is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Normal Map", "water_normal.png",
            "PNG image (*.png);;TGA image (*.tga);;TIFF image (*.tiff)"
        )
        if not path:
            return
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".png")
        if target.exists():
            answer = QMessageBox.question(self, "Overwrite file?",
                f"{target} already exists. Replace it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            save_normal_map(self.current_image, target)
            self.status.setText(f"Exported: {target.name}")
            QMessageBox.information(self, "Export complete", f"Saved normal map to:\n{target}")
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_image is not None:
            h, w, _ = self.current_image.shape
            qimage = QImage(self.current_image.data, w, h, 3*w, QImage.Format.Format_RGB888).copy()
            self.preview.setPixmap(QPixmap.fromImage(qimage).scaled(
                self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

