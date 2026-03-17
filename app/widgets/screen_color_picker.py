"""Full-screen eyedropper color picker — click anywhere on screen to grab a color."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QWidget


class ScreenColorPicker(QWidget):
    """Fullscreen overlay that lets the user click any pixel to pick its color.

    Shows a magnified preview around the cursor with crosshair and hex readout.
    Press Escape to cancel.
    """

    color_picked = pyqtSignal(str)  # emits hex like "#FF0000"

    ZOOM = 8          # magnification factor
    GRID = 15         # grid size in pixels (must be odd for center pixel)
    PREVIEW_SIZE = GRID * ZOOM  # total preview widget size

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)

        # Grab the entire virtual desktop
        self._screenshot: QPixmap | None = None
        self._current_color = QColor(0, 0, 0)

        # Preview label follows the cursor
        self._preview = QLabel()
        self._preview.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self._preview.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._preview.setFixedSize(self.PREVIEW_SIZE + 2, self.PREVIEW_SIZE + 30)

        # Update timer for smooth tracking
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60fps
        self._timer.timeout.connect(self._update_preview)

    def start(self) -> None:
        """Capture the screen and show the picker overlay."""
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return

        # Grab the full virtual desktop across all screens
        vg = QGuiApplication.primaryScreen().virtualGeometry()
        self._screenshot = screen.grabWindow(
            0, vg.x(), vg.y(), vg.width(), vg.height()
        )
        self._vg = vg

        # Make the overlay cover the full virtual desktop
        self.setGeometry(vg)
        self.showFullScreen()
        self._preview.show()
        self._timer.start()

    def _update_preview(self) -> None:
        """Redraw the magnified preview at the current cursor position."""
        if not self._screenshot:
            return

        pos = QCursor.pos()
        # Map global cursor pos to screenshot coordinates
        sx = pos.x() - self._vg.x()
        sy = pos.y() - self._vg.y()

        half = self.GRID // 2
        # Extract the region around the cursor
        region = self._screenshot.copy(
            sx - half, sy - half, self.GRID, self.GRID
        )
        # Get the center pixel color
        img = self._screenshot.toImage()
        if 0 <= sx < img.width() and 0 <= sy < img.height():
            self._current_color = QColor(img.pixel(sx, sy))

        # Build the preview pixmap
        psize = self.PREVIEW_SIZE
        preview_pix = QPixmap(psize + 2, psize + 30)
        preview_pix.fill(QColor(0, 0, 0, 0))

        painter = QPainter(preview_pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Draw magnified region
        scaled = region.scaled(
            psize, psize, Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        painter.drawPixmap(1, 1, scaled)

        # Border
        painter.setPen(QColor("#2A2A44"))
        painter.drawRect(0, 0, psize + 1, psize + 1)

        # Crosshair on center pixel
        cx = half * self.ZOOM + 1
        cy = half * self.ZOOM + 1
        painter.setPen(QColor("#00FFFF"))
        painter.drawRect(cx, cy, self.ZOOM, self.ZOOM)

        # Color info bar at bottom
        painter.fillRect(0, psize + 2, psize + 2, 28, QColor("#0A0A0F"))
        painter.setPen(QColor("#00FFFF"))
        painter.setFont(painter.font())
        hex_str = self._current_color.name().upper()
        painter.drawText(4, psize + 20, hex_str)

        # Small swatch
        painter.setBrush(self._current_color)
        painter.setPen(QColor("#2A2A44"))
        painter.drawRect(psize - 24, psize + 5, 20, 20)

        painter.end()

        self._preview.setPixmap(preview_pix)

        # Position preview offset from cursor
        offset_x, offset_y = 20, 20
        preview_x = pos.x() + offset_x
        preview_y = pos.y() + offset_y

        # Keep on screen
        screen_geo = self._vg
        if preview_x + self._preview.width() > screen_geo.right():
            preview_x = pos.x() - offset_x - self._preview.width()
        if preview_y + self._preview.height() > screen_geo.bottom():
            preview_y = pos.y() - offset_y - self._preview.height()

        self._preview.move(preview_x, preview_y)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.color_picked.emit(self._current_color.name().upper())
            self._close()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._close()

    def _close(self) -> None:
        self._timer.stop()
        self._preview.hide()
        self.hide()
        self._screenshot = None
