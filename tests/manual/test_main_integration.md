# Main Application Integration Test

## Purpose
Verify keyboard monitoring integration in main run command.

## Prerequisites
- User in `input` group
- Physical keyboard connected
- Config file at `~/.config/talk-it-out/config.toml` with combos defined

## Test Procedure

### 1. Start Application

```bash
uv run python -m talk_it_out.main run --log-level INFO
```

**Expected output:**
```
application_started: config_path=/home/user/.config/talk-it-out/config.toml
keyboard_monitoring_started: combos=['record_for_paste']
```

### 2. Press Combo Keys

Press Super+Alt together.

**Expected output:**
```
combo_activated: combo=record_for_paste device=/dev/input/event3
```

### 3. Release Combo Keys

Release Super+Alt.

**Expected output:**
```
combo_released: combo=record_for_paste device=/dev/input/event3
```

### 4. Press Ctrl-C

**Expected output:**
```
keyboard_monitor_stopping
keyboard_device_closed: path=/dev/input/event3
keyboard_monitor_stopped
shutdown_complete
```

### 5. Verify Clean Exit

Command should exit with status 0, no error messages.

## Troubleshooting

**No devices found:**
- Check `groups` includes `input`
- Reboot may be required after adding to group

**Permission denied:**
- Check `/dev/input/event*` permissions
- Verify user in input group: `groups | grep input`

**No combo_activated logs:**
- Verify config has correct combo definition
- Try DEBUG log level to see key events: `--log-level DEBUG`
- Check device path in logs matches your keyboard
