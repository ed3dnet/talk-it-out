# pattern: Imperative Shell
# Interactive audio device selection command

import sys
from talk_it_out.framework import config, config_io

try:
    import sounddevice as sd
except ImportError:
    sd = None


def select_audio_device() -> int:
    """Interactive audio device selection.

    Lists all available input devices and prompts user to select one.
    Updates config file with selected device.

    Returns:
        0 on success, 1 on error
    """
    # Check if sounddevice is available
    if sd is None:
        print("❌ sounddevice library not installed", file=sys.stderr)
        print("Install with: uv add sounddevice", file=sys.stderr)
        return 1

    try:
        # Get all devices and default
        devices = sd.query_devices()
        default_device = sd.query_devices(kind='input')
        default_idx = default_device.get('index')

        # Filter input devices
        input_devices = []
        for idx, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                is_default = " (current system default)" if idx == default_idx else ""
                input_devices.append((idx, device, is_default))

        if not input_devices:
            print("❌ No input devices found", file=sys.stderr)
            return 1

        # Display menu
        print("\nAvailable audio input devices:\n")
        print("  0: System default")

        for menu_idx, (dev_idx, device, is_default) in enumerate(input_devices, start=1):
            print(
                f"  {menu_idx}: {device['name']} "
                f"({device['max_input_channels']} channels, "
                f"{int(device['default_samplerate'])} Hz){is_default}"
            )

        # Get user selection
        print()
        try:
            selection = int(input("Select device number: "))
        except (ValueError, EOFError):
            print("❌ Invalid selection", file=sys.stderr)
            return 1

        # Process selection
        if selection == 0:
            # System default - remove device from config or set to empty string
            selected_name = ""
            print("\n✓ Selected: System default")
        elif 1 <= selection <= len(input_devices):
            # Specific device - store device name
            _, device, _ = input_devices[selection - 1]
            selected_name = device['name']
            print(f"\n✓ Selected: {selected_name}")
        else:
            print(f"❌ Invalid selection: {selection}", file=sys.stderr)
            return 1

        # Load current config
        config_path = config.get_config_path()
        cfg = config_io.load_config(config_path)

        # Update device setting
        cfg["audio"]["device"] = selected_name

        # Save config
        config_io.save_config(config_path, cfg)
        print(f"\n✓ Configuration updated: {config_path}")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
