"""Reusable color swatch widget showing a colored rectangle + hex text."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget


class ColorSwatchWidget(QWidget):
    """Small color swatch with optional hex label."""

    def __init__(
        self,
        color_hex: str = "#FFFFFF",
        size: int = 24,
        show_label: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._color_hex = color_hex
        self._size = size

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._swatch = _SwatchRect(color_hex, size)
        layout.addWidget(self._swatch)

        self._label = QLabel(color_hex.upper())
        self._label.setStyleSheet(
            "color: #E0E0F0; font-family: 'Consolas', monospace; "
            "font-size: 13px; background: transparent;"
        )
        if show_label:
            layout.addWidget(self._label)
        else:
            self._label.hide()

        layout.addStretch()

    def set_color(self, color_hex: str) -> None:
        self._color_hex = color_hex
        self._swatch.set_color(color_hex)
        self._label.setText(color_hex.upper())

    def color_hex(self) -> str:
        return self._color_hex


class _SwatchRect(QWidget):
    """Painted color rectangle."""

    def __init__(self, color_hex: str, size: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = QColor(color_hex)
        self.setFixedSize(size, size)

    def set_color(self, color_hex: str) -> None:
        self._color = QColor(color_hex)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#2A2A44"))
        painter.setBrush(self._color)
        painter.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 3, 3)
        painter.end()
