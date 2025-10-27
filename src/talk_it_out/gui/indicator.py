# pattern: Imperative Shell
"""
RecordingIndicator: Floating pill-shaped overlay showing workflow state.

States:
- Hidden: Not visible (idle)
- Recording: Red pill, brightness varies with audio volume
- Transcribing: Blue pill, brightness pulses
"""

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QPainter, QColor
import math
import structlog


class RecordingIndicator(QWidget):
    """Floating pill indicator (48x12px) showing recording/transcription state"""

    def __init__(self):
        super().__init__()

        self.log = structlog.get_logger()

        # Prevent focus stealing
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Window configuration for floating overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Fixed size: 48px × 12px pill
        self.setFixedSize(48, 12)

        # State tracking
        self.state = "hidden"  # "hidden", "recording", "transcribing"
        self.audio_level = 0.0  # 0.0-1.0

        # Pulsing for transcribing state
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self._pulse_update)
        self.pulse_phase = 0.0  # 0.0 to 2π

        # Position on screen
        self._position_on_screen()

        # Start hidden
        self.hide()

    def _position_on_screen(self):
        """Position indicator centered horizontally, 96px from top"""
        screen = QApplication.primaryScreen()
        if screen is None:
            self.log.warning("no_primary_screen_found")
            return

        screen_geometry = screen.availableGeometry()

        # Center horizontally
        x = screen_geometry.x() + (screen_geometry.width() - 48) // 2
        # 96px from top
        y = screen_geometry.y() + 96

        self.move(x, y)
        self.log.debug("indicator_positioned", x=x, y=y)

    def paintEvent(self, event):
        """Draw pill with color based on state"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.state == "recording":
            # Red: brightness varies with audio level (dark 100 → bright 255)
            brightness = int(100 + 155 * self.audio_level)
            color = QColor(brightness, 0, 0)
        elif self.state == "transcribing":
            # Blue: brightness pulses (100 → 255)
            brightness = int(100 + 155 * abs(math.sin(self.pulse_phase)))
            color = QColor(0, 50, brightness)
        else:
            # Hidden state - don't draw anything
            return

        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        # Draw rounded rectangle: 6px radius = pill shape
        painter.drawRoundedRect(0, 0, 48, 12, 6, 6)

    @pyqtSlot()
    def _pulse_update(self):
        """Update pulse phase for transcribing animation"""
        self.pulse_phase += 0.15  # Increment phase
        if self.pulse_phase > 2 * math.pi:
            self.pulse_phase = 0.0
        self.update()  # Trigger repaint

    @pyqtSlot()
    def show_recording(self):
        """Show indicator in recording state (red)"""
        self.log.debug("indicator_show_recording")
        self.state = "recording"
        self.audio_level = 0.0
        self.show()
        self.update()

    @pyqtSlot(float)
    def update_audio_level(self, level: float):
        """Update audio level and repaint (recording state)"""
        if self.state != "recording":
            return

        self.audio_level = max(0.0, min(1.0, level))  # Clamp to 0.0-1.0
        self.update()

    @pyqtSlot()
    def show_transcribing(self):
        """Show indicator in transcribing state (blue pulse)"""
        self.log.debug("indicator_show_transcribing")
        self.state = "transcribing"
        self.pulse_phase = 0.0
        self.pulse_timer.start(50)  # 50ms interval = ~20fps
        self.show()
        self.update()

    @pyqtSlot()
    def hide_indicator(self):
        """Hide indicator (idle state)"""
        self.log.debug("indicator_hide")
        self.state = "hidden"
        self.pulse_timer.stop()
        self.hide()
