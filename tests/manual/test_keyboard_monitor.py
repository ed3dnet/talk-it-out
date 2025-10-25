#!/usr/bin/env python3
"""Manual test script for KeyboardMonitor.

Run this script and press Super+Alt to verify combo detection.
Press Ctrl-C to exit.

Usage:
    uv run python tests/manual/test_keyboard_monitor.py
"""

import queue
import signal
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from talk_it_out.framework import keyboard, keyboard_io, logging_setup

def main():
    # Setup logging
    log = logging_setup.configure_logging("DEBUG")
    log.info("manual_test_starting")

    # Create test config with Super+Alt combo
    test_config = {
        "keys": {
            "combos": {
                "test_combo": {
                    "keys": ["Super", "Alt"]
                }
            }
        }
    }

    # Convert config to target combos
    target_combos = keyboard.config_to_target_combos(test_config)

    # Create event queue
    event_queue = queue.Queue()

    # Create and start monitor
    monitor = keyboard_io.KeyboardMonitor(target_combos, event_queue)

    # Setup Ctrl-C handler
    def cleanup(signum, frame):
        log.info("manual_test_cleanup")
        monitor.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)

    # Start monitoring
    monitor.start()

    log.info("manual_test_ready", message="Press Super+Alt to test combo detection")
    log.info("manual_test_ready", message="Press Ctrl-C to exit")

    # Process events
    try:
        while True:
            try:
                event = event_queue.get(timeout=1.0)
                log.info(
                    "combo_event_received",
                    type=event.event_type,
                    combo=event.combo_type,
                    device=event.device_path
                )
            except queue.Empty:
                pass
    except KeyboardInterrupt:
        cleanup(None, None)

if __name__ == "__main__":
    main()
