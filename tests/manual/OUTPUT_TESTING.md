# Manual Testing Checklist - Output Strategy

## Prerequisites

- [ ] wl-clipboard installed (`which wl-copy wl-paste`)
- [ ] ydotool installed (`which ydotool`)
- [ ] ydotoold daemon running (`systemctl status ydotoold`)
- [ ] Wayland session (check `echo $XDG_SESSION_TYPE`)

## Basic Paste Workflow

- [ ] **Terminal application paste**
  - Open terminal (GNOME Terminal, Konsole, etc.)
  - Run `talk-it-out run`
  - Press Meta+Alt, speak "hello world", release
  - Verify "hello world" appears in terminal
  - Note: Should use Shift+Insert, not Ctrl+V

- [ ] **Browser textarea paste**
  - Open browser, navigate to text input field
  - Run `talk-it-out run`
  - Press Meta+Alt, speak "test input", release
  - Verify "test input" appears in textarea

- [ ] **Text editor paste**
  - Open text editor (Kate, gedit, VS Code, etc.)
  - Run `talk-it-out run`
  - Press Meta+Alt, speak "editor test", release
  - Verify text appears at cursor position

## Error Handling

- [ ] **Missing wl-copy**
  - Temporarily rename wl-copy: `sudo mv /usr/bin/wl-copy /usr/bin/wl-copy.bak`
  - Run `talk-it-out run`
  - Verify error message shows install instructions
  - Restore: `sudo mv /usr/bin/wl-copy.bak /usr/bin/wl-copy`

- [ ] **Missing ydotool**
  - Temporarily rename ydotool: `sudo mv /usr/bin/ydotool /usr/bin/ydotool.bak`
  - Run `talk-it-out run`
  - Verify error message shows install instructions
  - Restore: `sudo mv /usr/bin/ydotool.bak /usr/bin/ydotool`

- [ ] **ydotoold not running**
  - Stop daemon: `sudo systemctl stop ydotoold`
  - Run `talk-it-out run`
  - Verify error message mentions starting ydotoold
  - Start daemon: `sudo systemctl start ydotoold`

## Configuration Options

- [ ] **Custom ydotool socket**
  - Find ydotool socket: `ls -l /run/ydotool/`
  - Edit config, add:
    ```toml
    [output.wl-clip]
    ydotool_socket = "/run/ydotool/socket"  # Explicit path
    ```
  - Run test, verify paste works
  - Check logs show socket path verification

- [ ] **Socket permission errors**
  - Create unreadable socket test (requires root):
    ```bash
    sudo touch /tmp/test-socket
    sudo chmod 000 /tmp/test-socket
    ```
  - Edit config to use `/tmp/test-socket`
  - Run `talk-it-out run`
  - Verify error message mentions permissions and suggests fix
  - Cleanup: `sudo rm /tmp/test-socket`

- [ ] **Override clipboard target to clipboard only**
  - Edit config: `talk-it-out config-edit`
  - Add:
    ```toml
    [output.wl-clip]
    targets = ["clipboard"]
    ```
  - Run test, verify paste works
  - Check primary selection NOT set: `wl-paste --primary` (should differ)

- [ ] **Override clipboard target to primary only**
  - Edit config, change to:
    ```toml
    [output.wl-clip]
    targets = ["primary"]
    ```
  - Run test in terminal (terminals often use primary)
  - Verify paste works

- [ ] **Both targets (default)**
  - Remove `[output.wl-clip]` section from config
  - Run test
  - Verify both clipboards set:
    ```bash
    wl-paste          # Should show transcription
    wl-paste --primary  # Should also show transcription
    ```

## Stress Testing

- [ ] **Rapid consecutive pastes**
  - Run `talk-it-out run`
  - Trigger recording 3-4 times quickly (short utterances)
  - Verify all transcriptions paste correctly
  - Check logs for errors

- [ ] **Long transcription**
  - Record a long utterance (30+ seconds)
  - Verify entire transcription pastes correctly
  - Check no truncation or corruption

- [ ] **Special characters**
  - Speak text with punctuation: "Hello, world! How are you?"
  - Verify punctuation appears correctly in paste

## Debug Logging

- [ ] **Verify detailed logs**
  - Run with debug: `talk-it-out run --log-level DEBUG`
  - Trigger recording
  - Verify logs show:
    - `output_strategy_initialized`
    - `paste_operation_started`
    - `running_wl_copy`
    - `verifying_clipboard`
    - `clipboard_verified`
    - `waiting_for_virtual_device`
    - `sending_shift_insert`
    - `paste_operation_completed`

## Cleanup

- [ ] Return config to defaults (remove `[output.wl-clip]` overrides)
- [ ] Verify ydotoold still running: `systemctl status ydotoold`
