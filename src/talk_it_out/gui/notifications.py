# pattern: Imperative Shell
"""
NotificationManager: D-Bus desktop notifications for errors.

Uses FreeDesktop.org Desktop Notifications Specification via PyQt6's QtDBus.
Falls back to stderr if D-Bus unavailable.
"""

import sys
import structlog

from PyQt6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
from PyQt6.QtCore import QVariant


class NotificationManager:
    """Send desktop notifications via D-Bus (QtDBus)"""

    def __init__(self, app_name: str = "talk-it-out"):
        self.app_name = app_name
        self.log = structlog.get_logger()

        # Try to connect to D-Bus
        bus = QDBusConnection.sessionBus()
        if not bus.isConnected():
            self.log.warning("dbus_unavailable", fallback="stderr")
            self.notifications = None
            return

        # Create D-Bus interface for org.freedesktop.Notifications
        self.notifications = QDBusInterface(
            "org.freedesktop.Notifications",
            "/org/freedesktop/Notifications",
            "org.freedesktop.Notifications",
            bus
        )

        if not self.notifications.isValid():
            self.log.warning("notifications_interface_invalid", fallback="stderr")
            self.notifications = None
        else:
            self.log.info("notifications_initialized", backend="dbus")

    def send(self, summary: str, body: str, urgency: str = "normal"):
        """
        Send desktop notification.

        Args:
            summary: Notification title
            body: Notification message
            urgency: "low", "normal", or "critical"
        """
        if self.notifications is None:
            # Fallback to stderr
            print(f"[NOTIFICATION] {summary}: {body}", file=sys.stderr)
            return

        # Map urgency to D-Bus byte values
        urgency_map = {"low": 0, "normal": 1, "critical": 2}
        urgency_value = urgency_map.get(urgency, 1)

        try:
            # Call Notify method via QtDBus
            # Notify(app_name, replaces_id, app_icon, summary, body, actions, hints, timeout)
            reply = self.notifications.call(
                "Notify",
                self.app_name,           # app_name
                0,                        # replaces_id (0 = new notification)
                "",                       # app_icon (empty = default)
                summary,                  # summary
                body,                     # body
                [],                       # actions (none)
                {"urgency": QVariant(urgency_value)},  # hints
                5000                      # timeout (5 seconds)
            )

            if reply.type() == QDBusMessage.MessageType.ErrorMessage:
                self.log.warning("notification_failed", error=reply.errorMessage())
                print(f"[NOTIFICATION] {summary}: {body}", file=sys.stderr)
            else:
                notification_id = reply.arguments()[0] if reply.arguments() else 0
                self.log.debug("notification_sent", id=notification_id, summary=summary)

        except Exception as e:
            self.log.warning("notification_exception", error=str(e))
            # Fallback to stderr on error
            print(f"[NOTIFICATION] {summary}: {body}", file=sys.stderr)
