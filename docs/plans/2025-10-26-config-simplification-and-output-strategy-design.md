# Config Simplification and Output Strategy Design

## Overview

**Goal:** Simplify configuration UX by supporting user config overrides and implement clipboard-based output using wl-clipboard + ydotool.

**Success criteria:**
- Users only configure settings they care about (keyboard combo, whisper model/language)
- Advanced settings (beam_size, vad_filter, etc.) have working defaults
- Config validation accepts merged config (internal defaults + user overrides)
- Transcribed text pastes into current application via Shift+Insert
- Dependency checks provide actionable install instructions
- Output strategy architecture supports future alternatives

**Scope:**
- Phase 1: Config merge infrastructure
- Phase 2: Output strategy framework
- Phase 3: WlClipSimplePaste implementation
- Phase 4: Testing infrastructure
- Phase 5: Documentation updates

## Architecture

### Configuration System

**Two-layer approach:**

1. **Internal defaults** - `config.py:default_config()` function
   - All settings with sensible defaults
   - Schema documentation
   - Not user-editable

2. **User config** - `~/.config/talk-it-out/config.toml`
   - Only contains overrides
   - Minimal generated starter config
   - Can omit any setting with a default

**Config loading flow:**

```
config_io.py:load_config()
  ↓
1. Load user TOML from ~/.config/talk-it-out/config.toml
2. Get defaults from config.py:default_config()
3. merged = merge_configs(defaults, user)
4. validate_config(merged)
  ↓
Return merged config dict
```

**Merge function (pure, in config.py):**

```python
def merge_configs(defaults: dict, user: dict) -> dict:
    """Deep merge user config over defaults.

    Args:
        defaults: Complete config with all defaults
        user: User overrides (can be partial)

    Returns:
        Merged config dict

    Notes:
        - Deep merge at section level ([whisper], [audio], etc.)
        - Array replacement (not merge) for [keys.combos]
    """
```

**Validation changes:**
- `validate_config()` validates merged result (stays strict)
- User config can omit fields - validation happens after merge
- Errors only for invalid overrides, not missing fields

**Generated user config (first run):**

```toml
[keys.combos]
record_for_paste = [
    ["KEY_LEFTMETA", "KEY_LEFTALT"],
]

[whisper]
model = "turbo"
language = "en"

[output]
strategy = "wl-clip-simplepaste"
```

Users add `[audio]`, `[logging]`, `[output.wl-clip]` only if needed.

### Output Strategy System

**Directory structure:**

```
src/talk_it_out/output/
├── __init__.py          # Exports create_output_strategy, OutputStrategy, OutputError
├── base.py              # Abstract base class
├── factory.py           # Strategy creation
└── strategies/
    ├── __init__.py
    └── wl_clip.py       # WlClipSimplePaste implementation
```

**Base interface (`output/base.py`):**

```python
from abc import ABC, abstractmethod

class OutputStrategy(ABC):
    """Base class for output strategies."""

    @abstractmethod
    def paste_text(self, text: str) -> None:
        """Paste text into current application.

        Args:
            text: Text to paste

        Raises:
            OutputError: If paste operation fails
        """
        pass

    @abstractmethod
    def verify_dependencies(self) -> None:
        """Check required tools are available.

        Raises:
            OutputError: If dependencies missing with helpful message
        """
        pass

class OutputError(Exception):
    """Raised when output operation fails."""
    pass
```

**Factory (`output/factory.py`):**

```python
def create_output_strategy(config: dict) -> OutputStrategy:
    """Create output strategy from config.

    Args:
        config: Full config dict with [output] section

    Returns:
        OutputStrategy instance

    Raises:
        ValueError: If strategy unknown
    """
    strategy_name = config["output"]["strategy"]

    if strategy_name == "wl-clip-simplepaste":
        from .strategies.wl_clip import WlClipSimplePaste
        return WlClipSimplePaste(config["output"].get("wl-clip", {}))
    else:
        raise ValueError(f"Unknown output strategy: {strategy_name}")
```

**Default config for [output]:**

```python
# In default_config():
"output": {
    "strategy": "wl-clip-simplepaste",
    "wl-clip": {
        "targets": ["clipboard", "primary"],
    }
}
```

**Integration into main.py:**

```python
# In run() command:
output_strategy = create_output_strategy(cfg)
output_strategy.verify_dependencies()  # Fail fast on startup

# Later, when transcription completes:
output_strategy.paste_text(transcribed_text)
```

### WlClipSimplePaste Implementation

**File:** `src/talk_it_out/output/strategies/wl_clip.py`

**Pattern:** Functional Core / Imperative Shell

**Functional Core (pure functions):**

```python
def verify_clipboard_content(expected: str, actual: str) -> bool:
    """Exact text comparison for clipboard verification."""
    return expected == actual

def build_wl_copy_commands(text: str, targets: list[str]) -> list[tuple[list[str], str]]:
    """Build wl-copy command lists for each target.

    Returns:
        List of (command_args, input_text) tuples
    """
    commands = []
    for target in targets:
        if target == "clipboard":
            commands.append((["wl-copy", "--type", "text/plain"], text))
        elif target == "primary":
            commands.append((["wl-copy", "--primary", "--type", "text/plain"], text))
    return commands

def build_shift_insert_command() -> list[str]:
    """Build ydotool command for Shift+Insert.

    Key codes:
        42 = KEY_LEFTSHIFT
        110 = KEY_INSERT
    """
    return ["ydotool", "key", "42:1", "110:1", "110:0", "42:0"]
```

**Imperative Shell (class):**

```python
class WlClipSimplePaste(OutputStrategy):
    """Output strategy using wl-clipboard + ydotool.

    Workflow:
        1. Copy text to clipboard(s) via wl-copy
        2. Poll wl-paste to verify clipboard ready
        3. Delay for ydotool virtual device recognition
        4. Send Shift+Insert keystroke via ydotool
    """

    def __init__(self, config: dict):
        """Initialize from [output.wl-clip] config section."""
        self.targets = config.get("targets", ["clipboard", "primary"])
        self.clipboard_timeout = 2.0  # seconds
        self.poll_interval = 0.1  # seconds
        self.virtual_device_delay = 0.5  # seconds

    def verify_dependencies(self) -> None:
        """Check wl-copy, wl-paste, ydotool, ydotoold.

        Raises:
            OutputError: With install instructions if missing
        """
        # Check wl-copy --help (exit 0)
        # Check wl-paste --help (exit 0)
        # Check ydotool help (exit 0)
        # Check pgrep -x ydotoold (daemon running)
        # Build helpful error message with distro-specific install commands

    def paste_text(self, text: str) -> None:
        """Copy to clipboard, verify, then paste."""
        logger.info("paste_operation_started", text_length=len(text))

        self._copy_to_clipboard(text)
        self._verify_clipboard_ready(text)

        # Delay for ydotool virtual device recognition
        time.sleep(self.virtual_device_delay)

        self._send_shift_insert()
        logger.info("paste_operation_completed")

    def _copy_to_clipboard(self, text: str) -> None:
        """Run wl-copy for each configured target."""
        commands = build_wl_copy_commands(text, self.targets)
        for cmd, input_text in commands:
            logger.debug("running_wl_copy", command=cmd)
            result = subprocess.run(
                cmd,
                input=input_text.encode(),
                capture_output=True,
            )
            if result.returncode != 0:
                raise OutputError(f"wl-copy failed: {result.stderr.decode()}")

    def _verify_clipboard_ready(self, expected_text: str) -> None:
        """Poll wl-paste until content matches or timeout."""
        logger.debug("verifying_clipboard")
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > self.clipboard_timeout:
                raise OutputError(
                    f"Clipboard verification timeout after {self.clipboard_timeout}s"
                )

            result = subprocess.run(
                ["wl-paste"],
                capture_output=True,
            )

            if result.returncode == 0:
                actual = result.stdout.decode()
                if verify_clipboard_content(expected_text, actual):
                    logger.debug("clipboard_verified", elapsed_ms=int(elapsed * 1000))
                    return

            time.sleep(self.poll_interval)

    def _send_shift_insert(self) -> None:
        """Send Shift+Insert keystroke via ydotool."""
        cmd = build_shift_insert_command()
        logger.info("sending_shift_insert")
        logger.debug("running_ydotool", command=cmd)

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise OutputError(f"ydotool failed: {result.stderr.decode()}")
```

## Existing Patterns

**Config patterns discovered:**

From investigation of `/home/ed/Development/ed3dnet/talk-it-out/src/talk_it_out/framework/`:

1. **Config separation:** Functional Core (`config.py`) + Imperative Shell (`config_io.py`)
2. **Default generation:** `default_config()` function creates complete config dict
3. **Validation:** Strict `validate_config()` ensures all required fields present
4. **TOML format:** User-facing config as TOML with sections

**This design follows existing patterns:**
- Continues Functional Core / Imperative Shell separation
- Extends `default_config()` as source of truth for defaults
- Keeps strict validation but applies after merge
- Maintains TOML format for user config

**New pattern introduced:**
- Config layering/merging (user overrides + internal defaults)
- Rationale: Reduces user-facing complexity while maintaining validation rigor

**Output strategy follows existing patterns:**
- Uses Functional Core (pure verify/build functions) + Imperative Shell (WlClipSimplePaste class)
- Follows project's subprocess-based I/O approach (see `whisper_io.py`, `keyboard.py`)
- Uses structlog for logging with structured context
- Raises custom exceptions (`OutputError`) like existing `KeyboardMonitorError`

## Implementation Phases

### Phase 1: Config Merge Infrastructure

**Goal:** Support user config overrides with internal defaults

**Components:**
- `src/talk_it_out/framework/config.py`:
  - Add `merge_configs(defaults: dict, user: dict) -> dict` pure function
  - Update `default_config()` to include `[output]` section
- `src/talk_it_out/framework/config_io.py`:
  - Modify `load_config()` to merge before validating
  - Update `initialize_config()` to write minimal starter config
- `src/talk_it_out/framework/config.py`:
  - Add validation for `[output]` section

**Dependencies:** None (foundation layer)

**Testing:**
- `tests/framework/test_config_merge.py`: Test merge logic with various override scenarios
- Update `tests/framework/test_config.py`: Ensure validation accepts merged configs

**Verification:**
- Run existing config tests: `uv run pytest tests/framework/test_config.py -v`
- Run new merge tests: `uv run pytest tests/framework/test_config_merge.py -v`
- Manual: Delete `~/.config/talk-it-out/config.toml`, run `talk-it-out config-edit`, verify minimal config generated

### Phase 2: Output Strategy Framework

**Goal:** Create pluggable output strategy architecture

**Components:**
- `src/talk_it_out/output/__init__.py`: Export public API
- `src/talk_it_out/output/base.py`: `OutputStrategy` ABC, `OutputError` exception
- `src/talk_it_out/output/factory.py`: `create_output_strategy()` factory function
- `src/talk_it_out/output/strategies/__init__.py`: Empty init

**Dependencies:** Phase 1 (needs [output] config validation)

**Testing:**
- `tests/output/test_factory.py`: Test factory with known/unknown strategy names
- Test `OutputError` exception can be raised/caught

**Verification:**
- Run factory tests: `uv run pytest tests/output/test_factory.py -v`
- Import check: `uv run python -c "from talk_it_out.output import OutputStrategy, OutputError, create_output_strategy"`

### Phase 3: WlClipSimplePaste Implementation

**Goal:** Implement wl-clipboard + ydotool paste strategy

**Components:**
- `src/talk_it_out/output/strategies/wl_clip.py`: Full implementation with Functional Core + Imperative Shell

**Dependencies:** Phase 2 (needs base.py interface)

**Testing:**
- `tests/output/test_wl_clip_core.py`: Unit tests for pure functions
- `tests/output/test_wl_clip_integration.py`: Integration tests (real clipboard, mocked ydotool)
- Mark clipboard tests for single-threaded execution
- `pytest.ini`: Add clipboard marker configuration

**Verification:**
- Unit tests: `uv run pytest tests/output/test_wl_clip_core.py -v`
- Integration tests: `uv run pytest tests/output/test_wl_clip_integration.py -m clipboard -n 0 -v`
- Dependency check: Run `talk-it-out run` without wl-clipboard installed (expect helpful error)
- Dependency check: Stop ydotoold, run `talk-it-out run` (expect daemon error)

### Phase 4: Main Application Integration

**Goal:** Wire output strategy into transcription workflow

**Components:**
- `src/talk_it_out/main.py`:
  - Import `create_output_strategy` from `output`
  - Call `verify_dependencies()` in `run()` command startup
  - Call `paste_text(transcribed_text)` after transcription completes

**Dependencies:** Phase 3 (needs working WlClipSimplePaste)

**Testing:**
- No new automated tests (covered by Phase 3)
- Manual testing checklist: `tests/manual/OUTPUT_TESTING.md`

**Verification:**
- Full workflow: `uv run python -m talk_it_out.main run`
  - Trigger keyboard combo (Meta+Alt)
  - Speak into microphone
  - Verify transcribed text appears in active application
- Test in terminal application (uses Shift+Insert correctly)
- Test in browser textarea
- Test missing dependencies show helpful errors

### Phase 5: Documentation Updates

**Goal:** Document new config system and output requirements

**Components:**
- `README.md`:
  - Add wl-clipboard and ydotool to Prerequisites
  - Document ydotoold daemon requirement with systemctl commands
  - Update Configuration section to explain override behavior
  - Add note about clipboard tests running single-threaded
  - Add Troubleshooting section for paste failures
- `tests/manual/OUTPUT_TESTING.md`: Create manual testing checklist
- Update existing manual test checklist if needed

**Dependencies:** Phase 4 (needs working implementation to document)

**Testing:** N/A (documentation only)

**Verification:**
- Review README changes ensure prerequisites clear
- Follow install instructions on fresh system
- Verify troubleshooting steps resolve common issues

### Phase 6: Config Migration (Optional)

**Goal:** Help existing users migrate to simplified config

**Components:**
- Add informational logging on startup if user config contains all default values
- Suggest running config-edit to see minimal version

**Dependencies:** Phase 5 (needs user documentation)

**Testing:** Manual testing with existing full config files

**Verification:**
- Test with old-style full config (should work unchanged)
- Test with new-style minimal config (should work with merged defaults)
- Verify no breaking changes for existing users

## Additional Considerations

### Error Messages

**Dependency verification errors:**

```
Error: Required tools not found for output strategy 'wl-clip-simplepaste'

Missing: wl-copy, wl-paste
Install: sudo dnf install wl-clipboard    # Fedora/RHEL
         sudo apt install wl-clipboard    # Debian/Ubuntu
         sudo pacman -S wl-clipboard      # Arch

Missing: ydotool
Install: sudo dnf install ydotool         # Fedora/RHEL
         sudo apt install ydotool         # Debian/Ubuntu
         yay -S ydotool-git               # Arch (AUR)

ydotoold daemon not running:
Start: sudo systemctl start ydotoold
Enable: sudo systemctl enable ydotoold

See: https://github.com/ReimuNotMoe/ydotool
```

**Runtime errors:**
- Clipboard timeout: "Failed to verify clipboard content after 2.0s"
- ydotool failure: "Failed to send paste keystroke - ydotool exited with code 1. Is ydotoold running?"
- Invalid strategy: "Unknown output strategy: 'invalid'. Valid: wl-clip-simplepaste"

### Logging

**Structured logging throughout paste operation:**

```
INFO: paste_operation_started text_length=48
DEBUG: running_wl_copy command=['wl-copy', '--type', 'text/plain']
DEBUG: running_wl_copy command=['wl-copy', '--primary', '--type', 'text/plain']
DEBUG: verifying_clipboard
DEBUG: clipboard_verified elapsed_ms=120
INFO: sending_shift_insert
DEBUG: running_ydotool command=['ydotool', 'key', '42:1', '110:1', '110:0', '42:0']
INFO: paste_operation_completed
```

### Future Extensibility

**Design supports future output strategies:**

- X11-based paste (xdotool + xclip)
- Direct D-Bus text injection
- Custom command execution
- Network paste services

**Adding new strategy requires:**
1. Implement `OutputStrategy` interface in `output/strategies/new_strategy.py`
2. Register in `factory.py`
3. Add config validation for new strategy settings
4. Document in README

### Testing Notes

**Clipboard tests must run single-threaded:**
- Wayland clipboard is global state
- Parallel tests cause race conditions
- Use `pytest -m clipboard -n 0` for clipboard tests
- Document in README testing section

**Test isolation:**
- All tests use `--config /tmp/test-config.toml`
- Never modify `~/.config/talk-it-out/config.toml` during tests
- Clean up temp files after tests

**Manual testing required for:**
- Full paste workflow (automated tests can't verify text appears in target app)
- Different application types (terminal, browser, text editor)
- Keyboard focus timing issues
- Multiple rapid consecutive pastes
