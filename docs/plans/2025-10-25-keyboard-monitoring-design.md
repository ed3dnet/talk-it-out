# Keyboard Monitoring Design

## Overview

Implement key combination detection for voice-to-text recording trigger. Monitor all input devices, detect when configured key combinations (e.g., Super+Alt) are pressed/released, and emit events via queue for consumption by main application.

**Goals:**
- Detect key combinations across all input devices
- Maintain per-device state isolation (paired press/release events)
- Provide extensible combo registration system
- Integrate with existing CLI framework

**Success Criteria:**
- Press Super+Alt → `combo_pressed` event appears in queue
- Release keys → `combo_released` event appears in queue
- Both events from same device
- Manual testing verifies physical keyboard interaction

## Architecture

**Pattern:** Event-sourced state machine with FCIS separation

**Core approach:**
- **Functional Core** (`keyboard.py`): Pure reducer processes key events, returns new state + output events
- **Imperative Shell** (`keyboard_io.py`): Wraps evdev, manages devices, feeds events to reducer
- **Per-device state**: Each device has isolated `KeyboardState`, enforces paired events
- **Queue-based output**: `ComboEvent` objects pushed to queue for async consumption

## Existing Patterns

This design follows established codebase patterns:

**FCIS pattern** (from Phase 2 refactor):
- `config.py` (Functional Core) + `config_io.py` (Imperative Shell)
- Pure business logic separated from I/O operations

**Configuration system** (from `config.py`):
- `VALID_KEYS` dict maps key names to evdev constants
- Config validation returns list of error strings
- Helper functions convert config to runtime types

**Signal handling** (from `signals.py`):
- `CleanupRegistry` for graceful shutdown
- Cleanup functions registered at component initialization

**Logging** (from `logging_setup.py`):
- Structlog with stderr output
- DEBUG for detailed events, INFO for user actions

**Testing** (established in tests/framework/):
- Pure functions tested with simple assertions
- I/O tested manually or with integration tests
- Test names describe behavior

## Implementation Phases

### Phase 1: Configuration Updates

**Goal:** Extend config system to support multiple combo definitions

**Components:**
- Modify `src/talk_it_out/framework/config.py`:
  - Update `default_config()` to use `combos` dict instead of `combination` list
  - Update `validate_config()` to validate combos dict structure
  - Update `VALID_KEYS` usage in validation

**Changes:**
```python
# Old: "keys": {"combination": ["super", "alt"]}
# New: "keys": {"combos": {"record_for_paste": ["super", "alt"]}}
```

**Testing:**
- Update `tests/framework/test_config.py` to test combos dict
- Test validation rejects invalid combo names
- Test validation rejects empty combos dict

**Verification:**
```bash
uv run pytest tests/framework/test_config.py -v -k combos
```

### Phase 2: Pure Keyboard Logic (Functional Core)

**Goal:** Implement event-sourced state machine for key tracking

**Components:**
- Create `src/talk_it_out/framework/keyboard.py` (Functional Core)
  - `KeyboardState` dataclass (frozen, immutable)
  - `KeyEvent` dataclass (device_path, key_code, is_press)
  - `ComboEvent` dataclass (event_type, combo_type, device_path)
  - `process_key_event(state, event, target_combos)` reducer
  - `config_to_target_combos(cfg)` helper

**State structure:**
```python
@dataclass(frozen=True)
class KeyboardState:
    held_keys: frozenset[int]          # Currently pressed key codes
    active_combos: Set[ComboType]      # Which combos are active
```

**Reducer signature:**
```python
def process_key_event(
    state: KeyboardState,
    event: KeyEvent,
    target_combos: Dict[ComboType, frozenset[int]]
) -> Tuple[KeyboardState, List[ComboEvent]]:
    """
    Pure reducer: processes key event, returns (new_state, output_events).

    - On press: Add key to held_keys, check if any combo now complete
    - On release: Remove key from held_keys, check if any combo now broken
    - Returns combo_pressed/combo_released events as needed
    """
```

**Testing:**
- Create `tests/framework/test_keyboard.py`
- Test combo detection with various key orders
- Test state transitions (empty → keys held → combo active → released)
- Test per-device isolation (events from different devices don't interact)
- Test `config_to_target_combos()` conversion

**Verification:**
```bash
uv run pytest tests/framework/test_keyboard.py -v
```

### Phase 3: Device I/O Layer (Imperative Shell)

**Goal:** Wrap evdev, scan devices, feed events to reducer

**Components:**
- Create `src/talk_it_out/framework/keyboard_io.py` (Imperative Shell)
  - `KeyboardMonitor` class
  - Device scanning: Find all `/dev/input/event*` with `EV_KEY` capability
  - Event loop: Use `select()` for efficient multi-device monitoring
  - Per-device state management
  - Queue integration

**Class structure:**
```python
class KeyboardMonitor:
    def __init__(self, target_combos: Dict[ComboType, frozenset[int]],
                 event_queue: Queue):
        self.devices: Dict[str, InputDevice] = {}
        self.states: Dict[str, KeyboardState] = {}
        self.target_combos = target_combos
        self.event_queue = event_queue
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Scan devices, start monitoring thread"""
        # Open all /dev/input/event* with keyboard capability
        # Create thread that runs event loop

    def stop(self):
        """Stop thread, close devices"""
        # Clean shutdown, close all file descriptors

    def _event_loop(self):
        """Main loop: select() on devices, process events"""
        # Use select.select([d.fd for d in devices])
        # On event: call reducer, emit to queue
```

**Dependencies:**
- Already in pyproject.toml: `evdev>=1.6.0`

**Testing:**
- Manual testing with physical keyboard
- Integration test: Start monitor, press keys, verify queue receives events

**Verification:**
```bash
# Manual test script
uv run python -c "
from talk_it_out.framework import keyboard_io, keyboard
import queue
q = queue.Queue()
combos = {'test': frozenset([125, 56])}  # Super+Alt
m = keyboard_io.KeyboardMonitor(combos, q)
m.start()
print('Press Super+Alt...')
event = q.get(timeout=30)
print(f'Got event: {event}')
m.stop()
"
```

### Phase 4: Main Application Integration

**Goal:** Wire keyboard monitor into run command

**Components:**
- Modify `src/talk_it_out/main.py`:
  - Create event queue
  - Convert config to target_combos
  - Instantiate `KeyboardMonitor`
  - Register cleanup
  - Replace keep-alive loop with queue processing

**Integration points:**
```python
# After config load and logging setup...

# Convert config combos to evdev keycodes
target_combos = keyboard.config_to_target_combos(cfg)

# Create event queue
combo_queue = queue.Queue()

# Start monitor
monitor = keyboard_io.KeyboardMonitor(target_combos, combo_queue)
registry.register(monitor.stop)
monitor.start()

log.info("keyboard_monitoring_started", combos=list(target_combos.keys()))

# Event processing loop
try:
    while True:
        combo_event = combo_queue.get(timeout=1.0)

        if combo_event.event_type == 'combo_pressed':
            log.info("combo_activated", combo=combo_event.combo_type,
                    device=combo_event.device_path)

        elif combo_event.event_type == 'combo_released':
            log.info("combo_released", combo=combo_event.combo_type,
                    device=combo_event.device_path)

except queue.Empty:
    pass
```

**Testing:**
- Manual: Run app, press Super+Alt, verify logs show combo events
- Verify Ctrl-C triggers cleanup

**Verification:**
```bash
uv run python -m talk_it_out.main run --log-level INFO
# Press Super+Alt → see "combo_activated" log
# Release → see "combo_released" log
# Ctrl-C → see clean shutdown
```

### Phase 5: Error Handling

**Goal:** Handle device errors gracefully

**Error scenarios:**
- Device disconnected mid-operation → Log warning, remove from monitoring
- Permission denied on device → Skip device, log warning
- No keyboard devices found → Log error, continue (app still runs)
- Invalid config → Caught by existing validation

**Logging strategy:**
- DEBUG: Every key event (device path, keycode, press/release)
- INFO: Combo activated/released
- WARNING: Device errors, skipped devices
- ERROR: Critical failures

**Implementation:**
- Add try/except in device scanning
- Add try/except in event loop
- Add device removal on disconnect
- Use structlog for all logging

**Testing:**
- Manual: Unplug keyboard while running
- Manual: Run without input group membership (should fail with clear message)

**Verification:**
```bash
# Test permission error
groups | grep -q input || echo "Not in input group - should see error"
uv run python -m talk_it_out.main run

# Test device disconnect (manual - unplug keyboard)
```

### Phase 6: Documentation and Manual Testing

**Goal:** Document behavior, create test checklist

**Components:**
- Update `README.md` with keyboard monitoring status
- Create manual test checklist
- Document config changes

**Manual test checklist:**
- [ ] Press Super+Alt → logs show combo_pressed
- [ ] Release → logs show combo_released
- [ ] Both events from same device path
- [ ] Multiple rapid presses work correctly
- [ ] Ctrl-C shuts down cleanly
- [ ] With multiple keyboards, each tracked independently
- [ ] Invalid config shows validation error

**Documentation updates:**
- README: Note keyboard monitoring implemented
- Config example: Show combos dict format

**Verification:** Complete manual checklist, verify all items pass

### Phase 7: Config Migration Helper (Optional)

**Goal:** Help users migrate old config format

**Component:**
- Add migration logic in `config_io.load_config()`
- Detect old format, convert automatically
- Log warning about deprecated format

**Old → New:**
```python
# If config has "keys": {"combination": [...]}, convert to:
"keys": {"combos": {"record_for_paste": [...]}}
```

**Testing:**
- Test loading old config format
- Verify conversion happens
- Verify warning logged

**Verification:**
```bash
# Create old format config, verify it loads and migrates
```

### Phase 8: Integration Testing

**Goal:** Verify end-to-end behavior

**Tests:**
- Full startup sequence with keyboard monitoring
- Multiple combo activations
- Clean shutdown
- Config validation with combos

**Update integration test script:**
- Add test for keyboard monitoring logs appearing
- Verify no errors on startup

**Verification:**
```bash
./tests/integration/test_cli_framework.sh
# Should pass all existing tests + verify keyboard monitoring starts
```

## Additional Considerations

**Thread safety:**
- Event queue provides cross-thread communication
- No shared mutable state between threads
- select() timeout allows periodic shutdown checks

**Performance:**
- select() is efficient for multiple file descriptors
- Per-device state updates are O(1)
- Combo checking is O(combos * keys_in_combo)

**Future extensibility:**
- Multiple combo types ready (`'record_for_paste'`, `'quick_note'`, etc.)
- Easy to add combo-specific data in `ComboEvent`
- Can add hold duration tracking in `KeyboardState` if needed

**Device hot-plugging:**
- Current design scans devices once at startup
- Future: Add inotify watch on `/dev/input/` for dynamic device addition
- Requires additional thread or poll in select() loop
