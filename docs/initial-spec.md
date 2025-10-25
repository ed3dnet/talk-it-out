# Voice-to-Text Utility for Linux/KDE Plasma
## Complete Implementation Specification

---

## Project Overview

A voice-to-text utility that records audio while holding down a key combination (Super+Alt), transcribes it using Whisper, and pastes the result into the focused window.

**Target Platform:**
- Fedora 42
- KDE Plasma 6
- Wayland compositor

**Development Approach:**
- **Phase 1:** Command-line application for core functionality
- **Phase 2:** Qt6 system tray application

---

# Phase 1: Command-Line Application

## Objectives

Build and test core functionality:
1. Detect key hold/release for configurable key combination
2. Record audio while keys are held
3. Transcribe audio with Whisper
4. Insert transcribed text into focused window

## System Dependencies

### Fedora Packages
```bash
# For keyboard monitoring
sudo dnf install python3-xlib

# For audio recording
sudo dnf install portaudio portaudio-devel

# For text insertion
sudo dnf install ydotool

# For DBus interaction (usually pre-installed in KDE)
sudo dnf install python3-dbus

# For Whisper (if not already installed)
sudo dnf install python3-pip python3-devel
```

### Python Dependencies
```bash
pip install pynput sounddevice numpy scipy dbus-python openai-whisper
```

## Core Components

### 1. Keyboard Monitoring

**Library:** pynput
- **PyPI:** https://pypi.org/project/pynput/
- **Documentation:** https://pynput.readthedocs.io/en/latest/keyboard.html
- **Installation:** `pip install pynput`

**Key Detection Pattern:**
```python
from pynput import keyboard

class KeyboardMonitor:
    def __init__(self, key_combination):
        self.key_combination = set(key_combination)
        self.current_keys = set()
        self.recording = False

    def on_press(self, key):
        self.current_keys.add(key)
        if self.key_combination.issubset(self.current_keys) and not self.recording:
            self.recording = True
            # Start recording

    def on_release(self, key):
        if key in self.key_combination and self.recording:
            self.current_keys.discard(key)
            if not self.key_combination.issubset(self.current_keys):
                self.recording = False
                # Stop recording and process
```

**Supported Keys:**
- `keyboard.Key.cmd` or `keyboard.Key.cmd_l` / `keyboard.Key.cmd_r` (Super/Windows key)
- `keyboard.Key.alt` or `keyboard.Key.alt_l` / `keyboard.Key.alt_r`
- `keyboard.Key.ctrl` or `keyboard.Key.ctrl_l` / `keyboard.Key.ctrl_r`

### 2. Audio Recording

**Library:** sounddevice
- **PyPI:** https://pypi.org/project/sounddevice/
- **Documentation:** https://python-sounddevice.readthedocs.io/
- **Installation:** `pip install sounddevice numpy scipy`

**Recording Pattern:**
```python
import sounddevice as sd
import numpy as np
from scipy.io import wavfile
import queue

class AudioRecorder:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.audio_queue = queue.Queue()

    def callback(self, indata, frames, time, status):
        """Called by sounddevice for each audio block"""
        if status:
            print(f"Audio status: {status}")
        self.audio_queue.put(indata.copy())

    def start_recording(self):
        self.recording = True
        self.audio_queue = queue.Queue()
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self.callback
        )
        self.stream.start()

    def stop_recording(self):
        self.recording = False
        self.stream.stop()
        self.stream.close()

        # Collect all audio data
        audio_data = []
        while not self.audio_queue.empty():
            audio_data.append(self.audio_queue.get())

        if audio_data:
            return np.concatenate(audio_data, axis=0)
        return None

    def save_audio(self, audio_data, filename):
        wavfile.write(filename, self.sample_rate, audio_data)
```

**Audio Device Selection:**
```python
# List available devices
import sounddevice as sd
print(sd.query_devices())

# Set default device (optional)
sd.default.device = 'device_name'
```

### 3. Whisper Transcription

**Library:** openai-whisper
- **GitHub:** https://github.com/openai/whisper
- **Installation:** `pip install openai-whisper`

**You already know this, but for completeness:**
```python
import whisper

class Transcriber:
    def __init__(self, model_name='base'):
        self.model = whisper.load_model(model_name)

    def transcribe(self, audio_file):
        result = self.model.transcribe(audio_file)
        return result['text'].strip()
```

### 4. Text Insertion

**Two-step process:**
1. Put text in clipboard via Klipper (KDE's clipboard manager)
2. Simulate Ctrl+V to paste

#### 4a. Clipboard via DBus

**Library:** dbus-python
- **Installation:** `pip install dbus-python` or use system package

**Klipper DBus Interface:**
```python
import dbus

class ClipboardManager:
    def __init__(self):
        self.bus = dbus.SessionBus()
        self.klipper = self.bus.get_object(
            'org.kde.klipper',
            '/klipper'
        )
        self.interface = dbus.Interface(
            self.klipper,
            'org.kde.klipper.klipper'
        )

    def set_clipboard(self, text):
        self.interface.setClipboardContents(text)
```

**Citation:** https://gist.github.com/aeris/3308963

#### 4b. Paste Simulation via ydotool

**Setup ydotool:**
```bash
# Install
sudo dnf install ydotool

# Enable daemon
systemctl --user enable --now ydotoold

# Verify socket exists
ls -la /run/user/$(id -u)/.ydotool_socket
```

**Citation:** https://github.com/ReimuNotMoe/ydotool

**Paste Implementation:**
```python
import subprocess
import time

class PasteSimulator:
    def __init__(self):
        self.check_ydotool()

    def check_ydotool(self):
        """Verify ydotoold is running"""
        result = subprocess.run(
            ['systemctl', '--user', 'is-active', 'ydotoold'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError("ydotoold service is not running")

    def paste(self):
        """Simulate Ctrl+V keypress"""
        # Key codes: 29=Ctrl, 47=V
        # Format: keycode:1 (press), keycode:0 (release)
        subprocess.run([
            'ydotool', 'key',
            '29:1',  # Ctrl down
            '47:1',  # V down
            '47:0',  # V up
            '29:0'   # Ctrl up
        ])

    def type_text(self, text):
        """Alternative: directly type text (may have Unicode issues)"""
        subprocess.run(['ydotool', 'type', text])
```

**Note:** The clipboard+paste approach is more reliable for Unicode than direct typing.

## Phase 1 Application Structure

```
voice-to-text-cli/
├── main.py                 # Entry point
├── keyboard_monitor.py     # Keyboard detection
├── audio_recorder.py       # Audio recording
├── transcriber.py          # Whisper integration
├── text_inserter.py        # Clipboard + paste
├── config.py               # Configuration handling
└── requirements.txt        # Python dependencies
```

### Configuration File

**Location:** `~/.config/voice-to-text/config.json`

```json
{
  "key_combination": ["cmd", "alt"],
  "audio": {
    "sample_rate": 16000,
    "channels": 1,
    "device": null
  },
  "whisper": {
    "model": "base",
    "language": null
  },
  "paste_method": "clipboard"
}
```

### Main Application Flow

```python
#!/usr/bin/env python3
import sys
import tempfile
import os
from pynput import keyboard

# Import custom modules
from keyboard_monitor import KeyboardMonitor
from audio_recorder import AudioRecorder
from transcriber import Transcriber
from text_inserter import ClipboardManager, PasteSimulator

class VoiceToTextCLI:
    def __init__(self):
        self.recorder = AudioRecorder()
        self.transcriber = Transcriber()
        self.clipboard = ClipboardManager()
        self.paste_sim = PasteSimulator()

        # Configure key combination
        self.key_combo = {keyboard.Key.cmd, keyboard.Key.alt}
        self.current_keys = set()
        self.is_recording = False

    def on_press(self, key):
        self.current_keys.add(key)

        if self.key_combo.issubset(self.current_keys) and not self.is_recording:
            print("🎤 Recording started...")
            self.is_recording = True
            self.recorder.start_recording()

    def on_release(self, key):
        if key in self.key_combo and self.is_recording:
            self.current_keys.discard(key)

            if not self.key_combo.issubset(self.current_keys):
                print("⏸️  Recording stopped...")
                self.is_recording = False

                # Stop recording and get audio
                audio_data = self.recorder.stop_recording()

                if audio_data is not None and len(audio_data) > 0:
                    self.process_audio(audio_data)
                else:
                    print("❌ No audio recorded")
        else:
            self.current_keys.discard(key)

    def process_audio(self, audio_data):
        print("🔄 Transcribing...")

        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_file = f.name
            self.recorder.save_audio(audio_data, temp_file)

        try:
            # Transcribe
            text = self.transcriber.transcribe(temp_file)

            if text:
                print(f"📝 Transcribed: {text}")

                # Put in clipboard
                self.clipboard.set_clipboard(text)

                # Small delay to ensure clipboard is set
                import time
                time.sleep(0.1)

                # Paste
                self.paste_sim.paste()
                print("✅ Text pasted")
            else:
                print("❌ No text transcribed")

        finally:
            # Cleanup
            os.unlink(temp_file)

    def run(self):
        print("Voice-to-Text CLI Started")
        print(f"Press and hold {'+'.join([str(k) for k in self.key_combo])} to record")
        print("Press Ctrl+C to exit\n")

        # Start keyboard listener
        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        ) as listener:
            listener.join()

if __name__ == '__main__':
    try:
        app = VoiceToTextCLI()
        app.run()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
```

### Testing Checklist

- [ ] Keyboard detection works (prints when keys pressed/released)
- [ ] Audio recording captures microphone input
- [ ] Audio file saves correctly
- [ ] Whisper transcribes audio
- [ ] Clipboard receives text (check with `qdbus org.kde.klipper /klipper getClipboardContents`)
- [ ] Paste simulation works (Ctrl+V happens in focused window)
- [ ] End-to-end: speak → text appears in focused app

---

# Phase 2: Qt6 System Tray Application

## Objectives

Convert CLI app to system tray daemon:
1. System tray icon with status indication
2. Right-click context menu
3. Settings dialog
4. Persistent configuration
5. Autostart capability
6. Visual feedback for states
7. Error handling with notifications

## Additional Dependencies

### Fedora Packages
```bash
sudo dnf install python3-pyqt6 libnotify
```

### Python Dependencies
```bash
pip install PyQt6
```

## Additional Components

### 1. Qt Application Framework

**Library:** PyQt6
- **PyPI:** https://pypi.org/project/PyQt6/
- **Documentation:** https://doc.qt.io/qtforpython-6/
- **Installation:** `pip install PyQt6`

**Key Classes:**
- `QApplication` - Main application
- `QSystemTrayIcon` - System tray icon
- `QMenu` - Context menu
- `QSettings` - Configuration storage
- `QThread` - Background threading
- `QIcon` - Icons for different states

### 2. System Tray Implementation

```python
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QSettings, pyqtSignal, QObject

class TrayApp(QObject):
    # Signals for cross-thread communication
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    transcription_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # Load settings
        self.settings = QSettings('voice-to-text', 'VoiceToText')

        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon('icons/idle.png'))

        # Create menu
        self.create_menu()

        # Connect signals
        self.recording_started.connect(self.on_recording_started)
        self.recording_stopped.connect(self.on_recording_stopped)
        self.transcription_complete.connect(self.on_transcription_complete)
        self.error_occurred.connect(self.on_error)

        # Show tray icon
        self.tray_icon.show()

    def create_menu(self):
        menu = QMenu()

        # Toggle enable/disable
        self.toggle_action = QAction("Disable", self)
        self.toggle_action.triggered.connect(self.toggle_listening)
        menu.addAction(self.toggle_action)

        menu.addSeparator()

        # Settings
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        menu.addAction(settings_action)

        # Test
        test_action = QAction("Test Recording", self)
        test_action.triggered.connect(self.test_recording)
        menu.addAction(test_action)

        menu.addSeparator()

        # About
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)

        # Quit
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)

    def on_recording_started(self):
        self.tray_icon.setIcon(QIcon('icons/recording.png'))
        self.show_notification("Recording", "Listening...")

    def on_recording_stopped(self):
        self.tray_icon.setIcon(QIcon('icons/processing.png'))
        self.show_notification("Processing", "Transcribing...")

    def on_transcription_complete(self, text):
        self.tray_icon.setIcon(QIcon('icons/idle.png'))
        self.show_notification("Complete", f"Transcribed: {text[:50]}...")

    def on_error(self, message):
        self.tray_icon.setIcon(QIcon('icons/error.png'))
        self.show_notification("Error", message, is_error=True)

    def show_notification(self, title, message, is_error=False):
        icon = (QSystemTrayIcon.MessageIcon.Critical if is_error
                else QSystemTrayIcon.MessageIcon.Information)
        self.tray_icon.showMessage(title, message, icon, 3000)
```

### 3. Threading Architecture

**Important:** Qt requires GUI operations on main thread, but recording/transcription should be in background.

```python
from PyQt6.QtCore import QThread, pyqtSignal
import threading

class RecordingThread(QThread):
    finished = pyqtSignal(object)  # Emits audio data
    error = pyqtSignal(str)

    def __init__(self, recorder):
        super().__init__()
        self.recorder = recorder
        self.should_stop = threading.Event()

    def run(self):
        try:
            self.recorder.start_recording()
            self.should_stop.wait()  # Wait for stop signal
            audio_data = self.recorder.stop_recording()
            self.finished.emit(audio_data)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self.should_stop.set()

class TranscriptionThread(QThread):
    finished = pyqtSignal(str)  # Emits transcribed text
    error = pyqtSignal(str)

    def __init__(self, transcriber, audio_file):
        super().__init__()
        self.transcriber = transcriber
        self.audio_file = audio_file

    def run(self):
        try:
            text = self.transcriber.transcribe(self.audio_file)
            self.finished.emit(text)
        except Exception as e:
            self.error.emit(str(e))
```

### 4. Settings Dialog

```python
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                              QLabel, QComboBox, QCheckBox,
                              QPushButton, QGroupBox)

class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Voice-to-Text Settings")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Key binding group
        kb_group = QGroupBox("Key Binding")
        kb_layout = QVBoxLayout()

        # Simplified: just show current binding
        self.kb_label = QLabel(f"Current: {self.get_key_binding_text()}")
        kb_layout.addWidget(self.kb_label)

        # Button to change
        kb_button = QPushButton("Change Key Binding")
        kb_button.clicked.connect(self.change_key_binding)
        kb_layout.addWidget(kb_button)

        kb_group.setLayout(kb_layout)
        layout.addWidget(kb_group)

        # Audio group
        audio_group = QGroupBox("Audio")
        audio_layout = QVBoxLayout()

        # Device selection
        device_label = QLabel("Input Device:")
        self.device_combo = QComboBox()
        self.populate_audio_devices()
        audio_layout.addWidget(device_label)
        audio_layout.addWidget(self.device_combo)

        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)

        # Whisper group
        whisper_group = QGroupBox("Transcription")
        whisper_layout = QVBoxLayout()

        # Model selection
        model_label = QLabel("Whisper Model:")
        self.model_combo = QComboBox()
        self.model_combo.addItems(['tiny', 'base', 'small', 'medium', 'large'])
        whisper_layout.addWidget(model_label)
        whisper_layout.addWidget(self.model_combo)

        whisper_group.setLayout(whisper_layout)
        layout.addWidget(whisper_group)

        # Autostart
        self.autostart_check = QCheckBox("Start on login")
        layout.addWidget(self.autostart_check)

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Load current settings
        self.load_settings()

    def populate_audio_devices(self):
        import sounddevice as sd
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                self.device_combo.addItem(device['name'], i)

    def load_settings(self):
        # Load from QSettings
        model = self.settings.value('whisper/model', 'base')
        self.model_combo.setCurrentText(model)

        autostart = self.settings.value('autostart', False, type=bool)
        self.autostart_check.setChecked(autostart)

    def save_settings(self):
        # Save to QSettings
        self.settings.setValue('whisper/model', self.model_combo.currentText())
        self.settings.setValue('autostart', self.autostart_check.isChecked())

        # Handle autostart
        self.configure_autostart(self.autostart_check.isChecked())

        self.accept()
```

### 5. Autostart Configuration

```python
import os
from pathlib import Path

class AutostartManager:
    def __init__(self, app_name='voice-to-text'):
        self.app_name = app_name
        self.autostart_dir = Path.home() / '.config' / 'autostart'
        self.desktop_file = self.autostart_dir / f'{app_name}.desktop'

    def enable(self, exec_path):
        """Create autostart desktop entry"""
        self.autostart_dir.mkdir(parents=True, exist_ok=True)

        desktop_content = f"""[Desktop Entry]
Type=Application
Name=Voice to Text
Exec={exec_path}
Icon=microphone
X-KDE-autostart-after=panel
X-KDE-StartupNotify=false
"""

        self.desktop_file.write_text(desktop_content)

    def disable(self):
        """Remove autostart desktop entry"""
        if self.desktop_file.exists():
            self.desktop_file.unlink()

    def is_enabled(self):
        """Check if autostart is enabled"""
        return self.desktop_file.exists()
```

### 6. Integrated Application

```python
#!/usr/bin/env python3
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSlot
from pynput import keyboard

class VoiceToTextGUI:
    def __init__(self):
        # Qt Application
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Core components
        self.recorder = AudioRecorder()
        self.transcriber = Transcriber()
        self.clipboard = ClipboardManager()
        self.paste_sim = PasteSimulator()

        # GUI components
        self.tray = TrayApp()

        # Threads
        self.recording_thread = None
        self.transcription_thread = None

        # State
        self.enabled = True
        self.is_recording = False
        self.current_keys = set()
        self.key_combo = {keyboard.Key.cmd, keyboard.Key.alt}

        # Start keyboard listener
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        self.keyboard_listener.start()

    def on_key_press(self, key):
        if not self.enabled:
            return

        self.current_keys.add(key)

        if self.key_combo.issubset(self.current_keys) and not self.is_recording:
            self.start_recording()

    def on_key_release(self, key):
        if key in self.key_combo and self.is_recording:
            self.current_keys.discard(key)
            if not self.key_combo.issubset(self.current_keys):
                self.stop_recording()
        else:
            self.current_keys.discard(key)

    def start_recording(self):
        self.is_recording = True
        self.tray.recording_started.emit()

        self.recording_thread = RecordingThread(self.recorder)
        self.recording_thread.finished.connect(self.on_recording_finished)
        self.recording_thread.error.connect(self.on_error)
        self.recording_thread.start()

    def stop_recording(self):
        if self.recording_thread:
            self.recording_thread.stop()

    @pyqtSlot(object)
    def on_recording_finished(self, audio_data):
        self.is_recording = False
        self.tray.recording_stopped.emit()

        if audio_data is None or len(audio_data) == 0:
            self.tray.error_occurred.emit("No audio recorded")
            return

        # Save to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            temp_file = f.name
            self.recorder.save_audio(audio_data, temp_file)

        # Start transcription
        self.transcription_thread = TranscriptionThread(self.transcriber, temp_file)
        self.transcription_thread.finished.connect(self.on_transcription_finished)
        self.transcription_thread.error.connect(self.on_error)
        self.transcription_thread.start()

    @pyqtSlot(str)
    def on_transcription_finished(self, text):
        if text:
            self.tray.transcription_complete.emit(text)

            # Put in clipboard and paste
            try:
                self.clipboard.set_clipboard(text)
                import time
                time.sleep(0.1)
                self.paste_sim.paste()
            except Exception as e:
                self.tray.error_occurred.emit(f"Paste failed: {e}")
        else:
            self.tray.error_occurred.emit("No text transcribed")

    @pyqtSlot(str)
    def on_error(self, message):
        self.is_recording = False
        self.tray.error_occurred.emit(message)

    def run(self):
        # Startup checks
        self.verify_dependencies()

        # Run Qt event loop
        return self.app.exec()

    def verify_dependencies(self):
        """Check all dependencies on startup"""
        errors = []

        # Check ydotoold
        import subprocess
        result = subprocess.run(
            ['systemctl', '--user', 'is-active', 'ydotoold'],
            capture_output=True
        )
        if result.returncode != 0:
            errors.append("ydotoold service is not running")

        # Check audio devices
        import sounddevice as sd
        devices = sd.query_devices()
        has_input = any(d['max_input_channels'] > 0 for d in devices)
        if not has_input:
            errors.append("No audio input device found")

        # Check Klipper
        try:
            ClipboardManager()
        except Exception as e:
            errors.append(f"Klipper not available: {e}")

        if errors:
            message = "Startup errors:\n" + "\n".join(f"• {e}" for e in errors)
            self.tray.error_occurred.emit(message)
            self.enabled = False

if __name__ == '__main__':
    app = VoiceToTextGUI()
    sys.exit(app.run())
```

## Phase 2 Application Structure

```
voice-to-text-gui/
├── main.py                 # Entry point (Qt app)
├── tray_app.py             # System tray implementation
├── settings_dialog.py      # Settings UI
├── keyboard_monitor.py     # Keyboard detection (from Phase 1)
├── audio_recorder.py       # Audio recording (from Phase 1)
├── transcriber.py          # Whisper integration (from Phase 1)
├── text_inserter.py        # Clipboard + paste (from Phase 1)
├── threads.py              # Qt thread wrappers
├── autostart.py            # Autostart management
├── config.py               # Configuration (updated for QSettings)
├── icons/                  # Icon files
│   ├── idle.png
│   ├── recording.png
│   ├── processing.png
│   └── error.png
├── requirements.txt        # Python dependencies
└── voice-to-text.desktop   # Desktop entry template
```

## Installation & Deployment

### Creating Executable Entry Point

Create `/usr/local/bin/voice-to-text`:
```bash
#!/usr/bin/env python3
import sys
from pathlib import Path

# Add application directory to path
app_dir = Path(__file__).parent.parent / 'share' / 'voice-to-text'
sys.path.insert(0, str(app_dir))

from main import VoiceToTextGUI

if __name__ == '__main__':
    app = VoiceToTextGUI()
    sys.exit(app.run())
```

Make executable:
```bash
chmod +x /usr/local/bin/voice-to-text
```

### Desktop Entry

`/usr/share/applications/voice-to-text.desktop`:
```ini
[Desktop Entry]
Type=Application
Name=Voice to Text
Comment=Voice transcription utility
Exec=voice-to-text
Icon=microphone
Categories=Utility;Accessibility;
StartupNotify=false
Terminal=false
```

## Testing Checklist (Phase 2)

- [ ] Application starts without console
- [ ] System tray icon appears
- [ ] Right-click menu works
- [ ] Recording starts/stops with key combo
- [ ] Icon changes to reflect state
- [ ] Notifications appear for events
- [ ] Settings dialog opens and saves
- [ ] Autostart can be enabled/disabled
- [ ] Application handles errors gracefully
- [ ] Application exits cleanly
- [ ] Multiple record/transcribe cycles work
- [ ] No memory leaks during extended use

---

# Troubleshooting

## Common Issues

### ydotoold not running
```bash
systemctl --user status ydotoold
systemctl --user enable --now ydotoold
```

### pynput keyboard events not detected
- Check if `python3-xlib` is installed
- Verify listener is running in background thread
- Test with simple print statements

### Audio recording silent
```bash
# List devices
python3 -m sounddevice

# Test recording
arecord -d 5 test.wav
```

### Klipper not accessible
```bash
# Check if Klipper is running
qdbus org.kde.klipper /klipper getClipboardContents

# Restart Klipper
kquitapp6 klipper && klipper &
```

### Paste not working
- Verify ydotoold is running
- Check socket permissions
- Test with `ydotool type "test"`

---

# Performance Considerations

## Memory Management
- Clear audio buffers after transcription
- Unlink temporary files
- Avoid accumulating old recordings

## CPU Usage
- Whisper model size affects speed (tiny < base < small < medium < large)
- Consider using GPU for large models if available
- Recording thread should be lightweight

## Startup Time
- Load Whisper model lazily (on first use)
- Cache frequently used resources
- Minimize startup checks

---

# Security Considerations

## Permissions
- ydotool requires `/dev/uinput` access
- DBus requires session bus access (normal for user apps)
- Audio recording requires microphone permission

## Privacy
- Audio is processed locally (Whisper runs on-device)
- No network transmission of audio
- Temporary files should be in secure location (`/tmp`)
- Consider option to keep/delete audio files

---

# Future Enhancements

## Potential Features
- Multiple key binding profiles
- Language selection per recording
- Post-processing (capitalization, punctuation)
- History of transcriptions
- Export transcriptions
- Statistics (usage, accuracy)
- Hot-reload configuration
- Systray icon animation during recording

## Alternative Implementations
- Replace ydotool with custom uinput implementation
- Use Wayland protocols directly for paste (if standardized)
- Add support for different transcription backends
- Add voice commands for formatting

---

# Key Citations

## Documentation
- pynput: https://pynput.readthedocs.io/en/latest/
- sounddevice: https://python-sounddevice.readthedocs.io/
- PyQt6: https://doc.qt.io/qtforpython-6/
- ydotool: https://github.com/ReimuNotMoe/ydotool
- Whisper: https://github.com/openai/whisper

## Code Examples
- Klipper DBus: https://gist.github.com/aeris/3308963
- pynput hotkeys: https://nitratine.net/blog/post/how-to-make-hotkeys-in-python/
- Qt system tray: https://doc.qt.io/qt-6/qsystemtrayicon.html
- KDE autostart: https://userbase.kde.org/System_Settings/Autostart

## Specifications
- FreeDesktop Notifications: https://specifications.freedesktop.org/notification-spec/
- Desktop Entry Spec: https://specifications.freedesktop.org/desktop-entry-spec/

---

# Summary

## Phase 1 Deliverables
- Working CLI application
- All core functionality tested
- Configuration system
- Error handling

## Phase 2 Deliverables
- Qt6 GUI application
- System tray integration
- Settings dialog
- Autostart capability
- Visual feedback system
- Production-ready daemon

The phased approach allows for iterative testing and ensures core functionality is solid before adding GUI complexity.
