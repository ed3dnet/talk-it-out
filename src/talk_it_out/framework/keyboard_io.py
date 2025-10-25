# pattern: Imperative Shell
# Device I/O operations for keyboard monitoring

"""Keyboard device monitoring with error handling.

Error Handling Strategy:
- Device permission errors: Skip device, log WARNING, continue
- Device disconnection: Remove device, log WARNING, continue monitoring
- No devices found: Log WARNING with hint, continue app execution
- Event loop failures: Log WARNING, stop monitoring thread
- Thread timeout: Log WARNING, continue shutdown

Logging Levels:
- DEBUG: Individual key events, device open/close, non-keyboard devices
- INFO: Monitoring start/stop, combo events, device count
- WARNING: Device errors, permission issues, disconnections
- ERROR: Not used (all errors are recoverable)

All errors are handled gracefully - the application continues running
even if keyboard monitoring fails completely.
"""

import select
import threading
from queue import Queue
from typing import Dict, List, Optional
import structlog

from evdev import InputDevice, ecodes, list_devices
from talk_it_out.framework.keyboard import (
    KeyboardState,
    KeyEvent,
    ComboEvent,
    process_key_event,
    ComboType,
)

log = structlog.get_logger()


class KeyboardMonitor:
    """Monitors input devices for keyboard events and emits combo events.

    Scans all /dev/input/event* devices with EV_KEY capability, maintains
    per-device state, and feeds events through the pure keyboard reducer.
    Runs in background thread, emits ComboEvents to queue.
    """

    def __init__(
        self,
        target_combos: Dict[ComboType, List[frozenset[int]]],
        event_queue: Queue
    ):
        """Initialize keyboard monitor.

        Args:
            target_combos: Map of combo names to required key code sets
            event_queue: Queue to receive ComboEvent objects
        """
        self.target_combos = target_combos
        self.event_queue = event_queue
        self.devices: Dict[str, InputDevice] = {}
        self.states: Dict[str, KeyboardState] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def _scan_devices(self) -> None:
        """Scan /dev/input for keyboard devices and open them.

        Opens all devices with EV_KEY capability. Skips devices that
        cannot be opened (permission denied, etc.) with warning log.
        """
        device_paths = list_devices()

        for path in device_paths:
            try:
                device = InputDevice(path)

                # Check if device has keyboard capability (EV_KEY)
                capabilities = device.capabilities(absinfo=False)
                if ecodes.EV_KEY not in capabilities:
                    device.close()
                    log.debug(
                        "device_not_keyboard",
                        path=path,
                        name=device.name
                    )
                    continue

                # Initialize state for this device
                self.devices[path] = device
                self.states[path] = KeyboardState()

                log.debug(
                    "keyboard_device_opened",
                    path=path,
                    name=device.name
                )

            except (PermissionError, OSError) as e:
                log.warning(
                    "keyboard_device_skipped",
                    path=path,
                    reason=str(e)
                )

        log.info(
            "keyboard_scan_complete",
            device_count=len(self.devices)
        )

    def _close_devices(self) -> None:
        """Close all open input devices."""
        for path, device in self.devices.items():
            try:
                device.close()
                log.debug("keyboard_device_closed", path=path)
            except OSError as e:
                log.warning(
                    "keyboard_device_close_error",
                    path=path,
                    error=str(e)
                )

        self.devices.clear()
        self.states.clear()

    def _event_loop(self) -> None:
        """Main event loop: monitor devices and process key events.

        Uses select() to efficiently wait for events from multiple devices.
        Processes events through pure reducer and emits to queue.
        Runs until self.running is set to False.
        """
        while self.running:
            # Check if we have any devices
            if not self.devices:
                log.debug("event_loop_no_devices")
                threading.Event().wait(1.0)  # Sleep 1 second
                continue

            # Use select with timeout for responsive shutdown
            device_map = {dev.fd: path for path, dev in self.devices.items()}
            readable_fds = list(device_map.keys())

            try:
                ready, _, _ = select.select(readable_fds, [], [], 1.0)
            except (OSError, ValueError) as e:
                # Device was removed or FD became invalid
                log.warning(
                    "event_loop_select_error",
                    error=str(e),
                    device_count=len(self.devices)
                )
                break

            # Process events from ready devices
            # Collect disconnected devices for cleanup after loop
            disconnected_paths = []

            for fd in ready:
                path = device_map[fd]
                device = self.devices[path]

                try:
                    # Read events from this device
                    for evdev_event in device.read():
                        # Only process key events (EV_KEY)
                        if evdev_event.type != ecodes.EV_KEY:
                            continue

                        # Convert to our KeyEvent
                        # evdev_event.value: 1=press, 0=release, 2=repeat
                        if evdev_event.value == 2:
                            continue  # Ignore key repeat events

                        key_event = KeyEvent(
                            device_path=path,
                            key_code=evdev_event.code,
                            is_press=(evdev_event.value == 1)
                        )

                        log.debug(
                            "key_event",
                            device=path,
                            code=evdev_event.code,
                            press=key_event.is_press
                        )

                        # Process through pure reducer
                        current_state = self.states[path]
                        new_state, combo_events = process_key_event(
                            current_state,
                            key_event,
                            self.target_combos
                        )

                        # Update state
                        self.states[path] = new_state

                        # Emit combo events to queue
                        for combo_event in combo_events:
                            self.event_queue.put(combo_event)
                            log.debug(
                                "combo_event_emitted",
                                event_type=combo_event.event_type,
                                combo=combo_event.combo_type
                            )

                except (OSError, IOError) as e:
                    # Device disconnected - mark for cleanup
                    log.warning(
                        "device_disconnected",
                        path=path,
                        device_name=device.name,
                        error=str(e)
                    )
                    disconnected_paths.append(path)

            # Clean up disconnected devices outside iteration
            for path in disconnected_paths:
                device = self.devices[path]
                try:
                    device.close()
                except OSError:
                    pass
                del self.devices[path]
                del self.states[path]

    def start(self) -> None:
        """Start keyboard monitoring in background thread.

        Scans devices and starts event loop thread.
        """
        if self.running:
            log.warning("keyboard_monitor_already_running")
            return

        log.info("keyboard_monitor_starting")

        # Scan for devices
        self._scan_devices()

        if not self.devices:
            log.warning(
                "keyboard_monitor_no_devices_found",
                message="No keyboard devices found - check permissions and hardware",
                hint="Ensure user is in 'input' group: sudo usermod -aG input $USER"
            )
            # Continue anyway - app can still run without keyboard monitoring

        # Start event loop thread
        self.running = True
        self.thread = threading.Thread(
            target=self._event_loop,
            name="KeyboardMonitor",
            daemon=True
        )
        self.thread.start()

        log.info(
            "keyboard_monitor_started",
            device_count=len(self.devices),
            combos=list(self.target_combos.keys())
        )

    def stop(self) -> None:
        """Stop keyboard monitoring and cleanup.

        Stops event loop thread and closes all devices.
        Safe to call multiple times.
        """
        if not self.running:
            return

        log.info("keyboard_monitor_stopping")

        # Signal thread to stop
        self.running = False

        # Wait for thread to finish (with timeout)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                log.warning(
                    "keyboard_monitor_thread_timeout",
                    timeout_seconds=2.0,
                    message="Thread did not stop gracefully"
                )

        # Close all devices
        self._close_devices()

        log.info("keyboard_monitor_stopped")
