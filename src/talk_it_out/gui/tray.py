# pattern: Imperative Shell
"""
TrayIcon: System tray icon with quit menu.

Provides minimal tray presence (no settings dialog per design).
Dynamic icon colorization shows workflow state.
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QBrush, QColor
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
import structlog
import math


class TrayIcon(QSystemTrayIcon):
    """System tray icon with quit menu and state-based colorization"""

    def __init__(self, app):
        self.log = structlog.get_logger()

        # Pre-create icons for performance
        # 22x22 is standard for Linux system tray
        self.idle_icon = self._create_colored_icon(QColor(128, 128, 128))  # Gray
        self.loading_icon = self._create_colored_icon(QColor(58, 58, 58))  # Dark gray

        # Start with loading icon (Whisper initialization takes several seconds)
        super().__init__(self.loading_icon)

        # Set initial tooltip
        self.setToolTip("Talk It Out - Loading")

        # Create context menu
        menu = QMenu()

        # Quit action
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(app.quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

        # Animation state tracking
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self._pulse_update)
        self.pulse_phase = 0.0
        self.current_audio_level = 0.0
        self.smoothed_audio_level = 0.0
        self.current_state = 'loading'

        # Hide icon until Session is ready (Whisper initialization takes several seconds)
        # Will be shown by set_state_idle() when session_ready signal fires
        self.setVisible(False)

        self.log.info("tray_icon_created")

    def _create_colored_icon(self, color: QColor, size: int = 22) -> QIcon:
        """Create microphone icon with colored status badge overlay"""
        # Create base pixmap with transparency
        result_pixmap = QPixmap(size, size)
        result_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(result_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Load and draw base microphone icon from system theme
        theme_icon = QIcon.fromTheme("audio-input-microphone")
        if not theme_icon.isNull():
            # Draw the microphone icon as base
            mic_pixmap = theme_icon.pixmap(size, size)
            painter.drawPixmap(0, 0, mic_pixmap)
        else:
            # Fallback: draw a simple microphone-like shape if theme icon not available
            painter.setBrush(QBrush(QColor(128, 128, 128)))
            painter.setPen(Qt.PenStyle.NoPen)
            # Draw circle for mic capsule
            painter.drawEllipse(int(size * 0.3), int(size * 0.1), int(size * 0.4), int(size * 0.5))

        # Draw colored status badge at 75% right, 75% down
        # Badge size is 50% of icon width
        badge_diameter = int(size * 0.5)
        badge_x = int(size * 0.75 - badge_diameter / 2)
        badge_y = int(size * 0.75 - badge_diameter / 2)

        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(badge_x, badge_y, badge_diameter, badge_diameter)

        painter.end()
        return QIcon(result_pixmap)

    def _interpolate_color(self, color1_hex: str, color2_hex: str, t: float) -> QColor:
        """Interpolate between two hex colors. t is 0.0-1.0"""
        # Parse hex colors
        r1, g1, b1 = int(color1_hex[1:3], 16), int(color1_hex[3:5], 16), int(color1_hex[5:7], 16)
        r2, g2, b2 = int(color2_hex[1:3], 16), int(color2_hex[3:5], 16), int(color2_hex[5:7], 16)

        # Linear interpolation
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)

        return QColor(r, g, b)

    def _pulse_update(self):
        """Update pulsing animation for transcribing state"""
        # Increment phase for 1 second pulse cycle at 50ms ticks (20 fps)
        # Phase increment = 2*pi / 20 ≈ 0.314
        self.pulse_phase += 0.314
        if self.pulse_phase > 2 * math.pi:
            self.pulse_phase = 0.0

        # Calculate interpolation factor using sine wave (0.0-1.0 range)
        t = (math.sin(self.pulse_phase) + 1.0) / 2.0

        # Interpolate between dark blue and light blue
        color = self._interpolate_color("#2A4D65", "#A7C6DA", t)
        icon = self._create_colored_icon(color)
        self.setIcon(icon)

    @pyqtSlot(float)
    def update_audio_level(self, level: float):
        """Update icon brightness based on audio level during recording"""
        # Only respond to audio level updates during recording state
        if self.current_state != 'recording':
            return

        # Store current level
        self.current_audio_level = level

        # Apply exponential moving average for smoothing
        # Alpha = 0.3 provides good responsiveness with smoothing
        alpha = 0.3
        self.smoothed_audio_level = alpha * level + (1 - alpha) * self.smoothed_audio_level

        # Apply nonlinear curve for better visibility at normal speaking volumes
        # Power curve with exponent 0.4 makes low/medium levels more responsive
        # Examples: 0.2 -> 0.45, 0.4 -> 0.66, 0.6 -> 0.79, 1.0 -> 1.0
        mapped_level = self.smoothed_audio_level ** 0.4

        # Interpolate between dark red/brown and light pink based on mapped level
        color = self._interpolate_color("#480E0A", "#FADDDB", mapped_level)
        icon = self._create_colored_icon(color)
        self.setIcon(icon)

    @pyqtSlot()
    def set_state_loading(self):
        """Set tray icon to loading state (dark gray)"""
        # Stop any ongoing animation
        self.pulse_timer.stop()

        # Update state
        self.current_state = 'loading'
        self.current_audio_level = 0.0
        self.smoothed_audio_level = 0.0
        self.pulse_phase = 0.0

        # Set static dark gray icon
        self.setIcon(self.loading_icon)
        self.setToolTip("Talk It Out - Loading")
        self.log.debug("tray_state_loading")

    @pyqtSlot()
    def set_state_idle(self):
        """Set tray icon to idle state (gray)"""
        # Stop any ongoing animation
        self.pulse_timer.stop()

        # Reset state
        self.current_state = 'idle'
        self.current_audio_level = 0.0
        self.smoothed_audio_level = 0.0
        self.pulse_phase = 0.0

        # Set static gray icon
        self.setIcon(self.idle_icon)
        self.setToolTip("Talk It Out - Idle")

        # Show icon if hidden (happens on first transition from loading state)
        self.setVisible(True)

        self.log.debug("tray_state_idle")

    @pyqtSlot()
    def set_state_recording(self):
        """Set tray icon to recording state (red with audio-responsive brightness)"""
        # Stop pulse timer if running
        self.pulse_timer.stop()

        # Update state
        self.current_state = 'recording'
        self.current_audio_level = 0.0
        self.smoothed_audio_level = 0.0

        # Set initial dark red icon (will be updated by audio level)
        color = self._interpolate_color("#480E0A", "#FADDDB", 0.0)
        icon = self._create_colored_icon(color)
        self.setIcon(icon)
        self.setToolTip("Talk It Out - Recording")
        self.log.debug("tray_state_recording")

    @pyqtSlot()
    def set_state_transcribing(self):
        """Set tray icon to transcribing state (pulsing blue)"""
        # Update state
        self.current_state = 'transcribing'

        # Reset pulse phase for smooth animation start
        self.pulse_phase = 0.0

        # Start pulse timer (50ms for smooth animation)
        self.pulse_timer.start(50)

        self.setToolTip("Talk It Out - Transcribing")
        self.log.debug("tray_state_transcribing")
