from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QImage, QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget


class TexturePreview(QWidget):
    """Interactive 2D texture viewer with tiling, channel inspection and comparison."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 500)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.result_image: np.ndarray | None = None
        self.source_image: np.ndarray | None = None
        self.view_mode = "Single"
        self.channel = "RGB"
        self.comparison = "Result"
        self.zoom = 1.0
        self.pan = QPointF(0.0, 0.0)
        self._drag_position: QPointF | None = None
        self.setStyleSheet("background: #15181d; border: 1px solid #3b414b; border-radius: 6px;")

    def set_images(self, result: np.ndarray | None, source: np.ndarray | None = None):
        self.result_image = result
        self.source_image = source
        self.update()

    def set_view_mode(self, mode: str):
        self.view_mode = mode
        self.update()

    def set_channel(self, channel: str):
        self.channel = channel
        self.update()

    def set_comparison(self, comparison: str):
        self.comparison = comparison
        self.update()

    def reset_view(self):
        self.zoom = 1.0
        self.pan = QPointF(0.0, 0.0)
        self.update()

    def _to_qimage(self, array: np.ndarray | None) -> QImage | None:
        if array is None:
            return None
        pixels = np.asarray(array)
        if pixels.ndim == 2:
            pixels = np.repeat(pixels[..., None], 3, axis=2)
        if pixels.ndim != 3 or pixels.shape[2] < 3:
            return None
        pixels = np.ascontiguousarray(pixels[..., :3], dtype=np.uint8)
        if self.channel in {"R", "G", "B"}:
            index = {"R": 0, "G": 1, "B": 2}[self.channel]
            channel_data = pixels[..., index:index + 1]
            pixels = np.repeat(channel_data, 3, axis=2)
        height, width, _ = pixels.shape
        return QImage(pixels.data, width, height, width * 3,
                      QImage.Format.Format_RGB888).copy()

    def _draw_image(self, painter: QPainter, image: QImage, area: QRectF):
        if image.isNull() or area.width() <= 0 or area.height() <= 0:
            return
        fit = min(area.width() / image.width(), area.height() / image.height())
        if self.view_mode == "3x3 Tiling":
            fit /= 3.0
        scale = max(0.02, fit * self.zoom)
        width = image.width() * scale
        height = image.height() * scale
        center = area.center() + self.pan
        if self.view_mode == "3x3 Tiling":
            for row in range(-1, 2):
                for col in range(-1, 2):
                    x = center.x() + col * width - width / 2
                    y = center.y() + row * height - height / 2
                    painter.drawImage(QRectF(x, y, width, height), image)
        else:
            painter.drawImage(QRectF(
                center.x() - width / 2, center.y() - height / 2, width, height
            ), image)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor("#15181d"))
        result = self._to_qimage(self.result_image)
        source = self._to_qimage(self.source_image)

        if self.comparison == "Side by side" and source is not None and result is not None:
            half = self.width() / 2
            left = QRectF(0, 0, half, self.height())
            right = QRectF(half, 0, self.width() - half, self.height())
            painter.setPen(QPen(QColor("#454d58"), 1))
            painter.drawLine(int(half), 0, int(half), self.height())
            self._draw_image(painter, source, left)
            self._draw_image(painter, result, right)
            painter.setPen(QColor("#d5dbe3"))
            painter.drawText(12, 24, "SOURCE")
            painter.drawText(int(half) + 12, 24, "RESULT")
        else:
            chosen = source if self.comparison == "Source" and source is not None else result
            if chosen is None:
                painter.setPen(QColor("#87919e"))
                painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                                 "Generate a texture or load a height image")
            else:
                self._draw_image(painter, chosen, QRectF(self.rect()))
                painter.setPen(QColor("#d5dbe3"))
                painter.drawText(12, 24, self.comparison.upper())
        painter.end()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1 / 1.15
        self.zoom = min(12.0, max(0.15, self.zoom * factor))
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_position is not None:
            current = event.position()
            self.pan += current - self._drag_position
            self._drag_position = current
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        self.update()
        super().resizeEvent(event)
