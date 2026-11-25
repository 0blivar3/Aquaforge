from __future__ import annotations

from pathlib import Path
import secrets
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal
from app.preview import TexturePreview
from app.preview_3d import NormalMap3DPreview
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QComboBox, QSpinBox,
    QDoubleSpinBox, QProgressBar, QFileDialog, QMessageBox,
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QScrollArea,
    QInputDialog, QTabWidget
)

from core.generator import GeneratorSettings, generate_heightmap
from core.native_backend import backend_name
from core.normal_math import height_to_normal
from core.image_to_normal import load_height_image, convert_height_image, CHANNELS
from core.presets import BUILTIN_PRESETS, load_custom_presets, save_custom_preset
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
            height = generate_heightmap(
                self.settings, lambda value: self.progress.emit(int(value * 0.7))
            )
            result = height_to_normal(
                height, strength=5.0, y_convention=self.convention,
                seamless=self.settings.seamless,
                progress=lambda value: self.progress.emit(70 + int(value * 0.3))
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class ImageConversionWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, height: np.ndarray, strength: float,
                 convention: str, seamless: bool):
        super().__init__()
        self.height = height
        self.strength = strength
        self.convention = convention
        self.seamless = seamless

    def run(self):
        try:
            self.finished.emit(convert_height_image(
                self.height, self.strength, self.convention, self.seamless
            ))
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AquaForge — Water Normal Map Generator")
        self.resize(1320, 860)
        self.current_image: np.ndarray | None = None
        self.source_image: np.ndarray | None = None
        self.source_height: np.ndarray | None = None
        self.source_path: Path | None = None
        self.seed = 12345
        self.thread: QThread | None = None
        self._loading_presets = False
        self.active_operation = "generation"
        self._build_ui()
        self._refresh_presets()

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

        preset_group = QGroupBox("Presets")
        preset_layout = QVBoxLayout(preset_group)
        self.preset_combo = QComboBox()
        self.preset_combo.currentTextChanged.connect(self._apply_selected_preset)
        self.save_preset_button = QPushButton("Save current settings as preset…")
        self.save_preset_button.clicked.connect(self._save_preset)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(self.save_preset_button)
        panel.addWidget(preset_group)

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

        actions = QGroupBox("Procedural generation")
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

        image_group = QGroupBox("Image to Normal")
        image_layout = QVBoxLayout(image_group)
        self.load_image_button = QPushButton("Load height image…")
        self.load_image_button.clicked.connect(self.load_source_image)
        image_layout.addWidget(self.load_image_button)
        image_form = QFormLayout()
        self.image_channel = QComboBox()
        self.image_channel.addItems(list(CHANNELS))
        self.image_channel.currentTextChanged.connect(self._reload_source_channel)
        self.image_strength = self._double(5.0, 0.0, 30.0, 0.25)
        image_form.addRow("Source channel", self.image_channel)
        image_form.addRow("Normal strength", self.image_strength)
        image_layout.addLayout(image_form)
        self.convert_button = QPushButton("Convert image to Normal Map")
        self.convert_button.setEnabled(False)
        self.convert_button.clicked.connect(self.convert_image)
        image_layout.addWidget(self.convert_button)
        panel.addWidget(image_group)

        panel.addStretch(1)
        controls_scroll.setWidget(controls)
        controls_scroll.setMinimumWidth(350)
        layout.addWidget(controls_scroll, 0)

        preview_panel = QVBoxLayout()
        self.preview_tabs = QTabWidget()

        two_d_page = QWidget()
        two_d_layout = QVBoxLayout(two_d_page)
        preview_header = QHBoxLayout()
        preview_header.addWidget(QLabel("2D TEXTURE PREVIEW"))
        preview_header.addStretch(1)
        self.info = QLabel("No texture loaded")
        preview_header.addWidget(self.info)
        two_d_layout.addLayout(preview_header)

        preview_controls = QHBoxLayout()
        self.preview_mode = QComboBox()
        self.preview_mode.addItems(["Single", "3x3 Tiling"])
        self.preview_mode.currentTextChanged.connect(self._set_preview_mode)
        self.preview_channel = QComboBox()
        self.preview_channel.addItems(["RGB", "R", "G", "B"])
        self.preview_channel.currentTextChanged.connect(self._set_preview_channel)
        self.preview_comparison = QComboBox()
        self.preview_comparison.addItems(["Result", "Source", "Side by side"])
        self.preview_comparison.currentTextChanged.connect(self._set_preview_comparison)
        self.reset_view_button = QPushButton("Reset View")
        self.reset_view_button.clicked.connect(self._reset_preview_view)
        preview_controls.addWidget(QLabel("View"))
        preview_controls.addWidget(self.preview_mode)
        preview_controls.addWidget(QLabel("Channel"))
        preview_controls.addWidget(self.preview_channel)
        preview_controls.addWidget(QLabel("Compare"))
        preview_controls.addWidget(self.preview_comparison)
        preview_controls.addStretch(1)
        preview_controls.addWidget(self.reset_view_button)
        two_d_layout.addLayout(preview_controls)

        animation_controls = QGroupBox("Animated preview")
        animation_layout = QHBoxLayout(animation_controls)
        self.animation_button = QPushButton("Play")
        self.animation_button.setCheckable(True)
        self.animation_button.setToolTip("Play or pause cyclic texture movement in the preview")
        self.animation_button.setEnabled(False)
        self.animation_button.toggled.connect(self._toggle_animation)
        self.animation_direction = QComboBox()
        self.animation_direction.addItems(["Right", "Left", "Down", "Up", "Diagonal"])
        self.animation_direction.currentTextChanged.connect(self.preview_direction_changed)
        self.animation_speed = self._double(1.0, 0.1, 3.0, 0.1)
        self.animation_speed.valueChanged.connect(self._animation_speed_changed)
        self.animation_intensity = self._double(1.0, 0.0, 2.0, 0.1)
        self.animation_intensity.valueChanged.connect(self._animation_intensity_changed)
        animation_layout.addWidget(self.animation_button)
        animation_layout.addWidget(QLabel("Direction"))
        animation_layout.addWidget(self.animation_direction)
        animation_layout.addWidget(QLabel("Speed"))
        animation_layout.addWidget(self.animation_speed)
        animation_layout.addWidget(QLabel("Motion"))
        animation_layout.addWidget(self.animation_intensity)
        two_d_layout.addWidget(animation_controls)

        self.preview = TexturePreview()
        two_d_layout.addWidget(self.preview, 1)
        self.preview_tabs.addTab(two_d_page, "2D Preview")

        three_d_page = QWidget()
        three_d_layout = QVBoxLayout(three_d_page)
        three_d_controls = QHBoxLayout()
        self.mesh_selector = QComboBox()
        self.mesh_selector.addItems(["Plane", "Cube", "Sphere", "Cylinder"])
        self.mesh_selector.currentTextChanged.connect(self._set_3d_mesh)
        self.uv_scale = self._double(1.0, 0.1, 12.0, 0.1)
        self.uv_scale.valueChanged.connect(self._set_3d_uv_scale)
        self.normal_preview_strength = self._double(1.0, 0.0, 3.0, 0.1)
        self.normal_preview_strength.valueChanged.connect(self._set_3d_normal_strength)
        self.preview_light = self._double(1.0, 0.0, 3.0, 0.1)
        self.preview_light.valueChanged.connect(self._set_3d_light_intensity)
        three_d_controls.addWidget(QLabel("Object"))
        three_d_controls.addWidget(self.mesh_selector)
        three_d_controls.addWidget(QLabel("UV tiling"))
        three_d_controls.addWidget(self.uv_scale)
        three_d_controls.addWidget(QLabel("Normal intensity"))
        three_d_controls.addWidget(self.normal_preview_strength)
        three_d_controls.addWidget(QLabel("Light"))
        three_d_controls.addWidget(self.preview_light)
        three_d_controls.addStretch(1)
        three_d_layout.addLayout(three_d_controls)
        self.preview_3d = NormalMap3DPreview()
        three_d_layout.addWidget(self.preview_3d, 1)
        three_d_hint = QLabel("Drag to rotate · Normal Map updates when a new result is generated")
        three_d_hint.setStyleSheet("color: #9ba5b3;")
        three_d_layout.addWidget(three_d_hint)
        self.preview_tabs.addTab(three_d_page, "3D Material Preview")
        preview_panel.addWidget(self.preview_tabs, 1)
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
            distortion=self.distortion.value(), seed=self.seed,
            seamless=self.seamless.isChecked()
        )

    def _set_settings(self, values: dict):
        widgets = {
            "wave_scale": self.wave_scale, "wave_strength": self.wave_strength,
            "frequency": self.frequency, "direction": self.direction,
            "wind_strength": self.wind, "ripple_intensity": self.ripple,
            "ripple_scale": self.ripple_scale, "detail": self.detail,
            "distortion": self.distortion,
        }
        for key, widget in widgets.items():
            if key in values:
                widget.setValue(values[key])

    def _refresh_presets(self):
        custom = load_custom_presets()
        self._custom_presets = custom
        self._loading_presets = True
        self.preset_combo.clear()
        self.preset_combo.addItems(list(BUILTIN_PRESETS) + list(custom))
        self._loading_presets = False
        self.preset_combo.setCurrentIndex(-1)

    def _apply_selected_preset(self, name: str):
        if self._loading_presets or not name:
            return
        values = BUILTIN_PRESETS.get(name, getattr(self, "_custom_presets", {}).get(name))
        if values:
            self._set_settings(values)
            self.status.setText(f"Preset applied: {name}")

    def _save_preset(self):
        name, accepted = QInputDialog.getText(self, "Save preset", "Preset name:")
        if not accepted:
            return
        try:
            save_custom_preset(name, self._settings())
            self._refresh_presets()
            index = self.preset_combo.findText(name.strip())
            if index >= 0:
                self.preset_combo.setCurrentIndex(index)
            self.status.setText(f"Preset saved: {name.strip()}")
        except Exception as exc:
            QMessageBox.warning(self, "Could not save preset", str(exc))

    def generate(self):
        if self.thread and self.thread.isRunning():
            return
        self.generate_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.progress.setValue(0)
        self.active_operation = "generation"
        self.status.setText(f"Generating with {backend_name()}…")
        worker = GenerationWorker(
            self._settings(),
            "OpenGL" if self.convention.currentIndex() == 0 else "DirectX"
        )
        self._start_worker(worker, worker.progress)

    def load_source_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load height image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)"
        )
        if not path:
            return
        self.source_path = Path(path)
        try:
            self._read_source_image()
            self.convert_button.setEnabled(True)
            self.preview_comparison.setCurrentText("Source")
            self.info.setText(f"Source: {self.source_image.shape[1]} × {self.source_image.shape[0]}")
            self.status.setText(f"Loaded height image: {self.source_path.name}")
        except Exception as exc:
            self.source_height = None
            self.source_image = None
            QMessageBox.critical(self, "Image loading error", str(exc))

    def _read_source_image(self):
        if self.source_path is None:
            return
        self.source_height, self.source_image = load_height_image(
            self.source_path, self.image_channel.currentText()
        )
        self._refresh_preview()

    def _reload_source_channel(self, _channel: str):
        if self.source_path is not None:
            try:
                self._read_source_image()
            except Exception as exc:
                QMessageBox.critical(self, "Image loading error", str(exc))

    def convert_image(self):
        if self.source_height is None or (self.thread and self.thread.isRunning()):
            return
        self.generate_button.setEnabled(False)
        self.convert_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.progress.setValue(0)
        self.active_operation = "conversion"
        self.status.setText("Converting image…")
        worker = ImageConversionWorker(
            self.source_height.copy(), self.image_strength.value(),
            "OpenGL" if self.convention.currentIndex() == 0 else "DirectX",
            self.seamless.isChecked()
        )
        self._start_worker(worker)

    def _start_worker(self, worker: QObject, progress_signal=None):
        self.thread = QThread(self)
        self.worker = worker
        worker.moveToThread(self.thread)
        self.thread.started.connect(worker.run)
        if progress_signal is not None:
            progress_signal.connect(self._on_progress)
        worker.finished.connect(self._on_generated)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(self.thread.quit)
        worker.failed.connect(self.thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        self.thread.finished.connect(self._thread_finished)
        self.thread.start()

    def _on_progress(self, value: int):
        self.progress.setValue(value)
        if self.active_operation == "generation":
            self.status.setText(
                f"Generating height field · {backend_name()}…" if value < 70
                else f"Converting height field to Normal Map · {backend_name()}…"
            )

    def _on_generated(self, image: np.ndarray):
        self.progress.setValue(100)
        self.current_image = image
        self.preview_comparison.setCurrentText("Result")
        self._refresh_preview()
        self.preview_3d.set_normal_map(image)
        h, w, _ = image.shape
        self.info.setText(f"{w} × {h} px")
        self.status.setText(
            "Image conversion complete" if self.active_operation == "conversion"
            else f"Generation complete · {backend_name()}"
        )
        self.export_button.setEnabled(True)
        self.animation_button.setEnabled(True)

    def _on_failed(self, message: str):
        self.status.setText("Operation failed")
        QMessageBox.critical(self, "Processing error", message)

    def _thread_finished(self):
        self.generate_button.setEnabled(True)
        self.convert_button.setEnabled(self.source_height is not None)
        self.thread = None

    def _refresh_preview(self):
        self.preview.set_images(self.current_image, self.source_image)

    def _set_preview_mode(self, mode: str):
        self.preview.set_view_mode(mode)

    def _set_preview_channel(self, channel: str):
        self.preview.set_channel(channel)

    def _set_preview_comparison(self, comparison: str):
        self.preview.set_comparison(comparison)

    def _reset_preview_view(self):
        self.preview.reset_view()

    def _set_3d_mesh(self, name: str):
        self.preview_3d.set_mesh(name)

    def _set_3d_uv_scale(self, value: float):
        self.preview_3d.set_uv_scale(value)

    def _set_3d_normal_strength(self, value: float):
        self.preview_3d.set_normal_strength(value)

    def _set_3d_light_intensity(self, value: float):
        self.preview_3d.set_light_intensity(value)

    def _toggle_animation(self, enabled: bool):
        self.preview.set_animation_enabled(enabled)
        self.animation_button.setText("Pause" if enabled else "Play")
        if enabled:
            self.status.setText("Animated preview running — export remains static")
        else:
            self.status.setText("Animated preview paused")

    def preview_direction_changed(self, direction: str):
        self.preview.set_animation_direction(direction)

    def _animation_speed_changed(self, value: float):
        self.preview.set_animation_speed(value)

    def _animation_intensity_changed(self, value: float):
        self.preview.set_animation_intensity(value)

    def randomize_seed(self):
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
            answer = QMessageBox.question(
                self, "Overwrite file?", f"{target} already exists. Replace it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
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
