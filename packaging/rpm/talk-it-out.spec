# pattern: Imperative Shell (handles packaging/installation)
%global pypi_name talk-it-out
%global pypi_name_underscore talk_it_out
%global pypi_version 0.1.0

Name:           %{pypi_name}
Version:        %{pypi_version}
Release:        1%{?dist}
Summary:        Voice-to-text for Linux using Whisper AI

License:        GPL-3.0-or-later
URL:            https://github.com/ed3dnet/talk-it-out
Source0:        %{pypi_name_underscore}-%{version}.tar.gz

BuildArch:      noarch

# Build dependencies
BuildRequires:  python3-devel >= 3.13
BuildRequires:  python3-build
BuildRequires:  python3-pip
BuildRequires:  python3-setuptools
BuildRequires:  pyproject-rpm-macros

# System library build dependencies
BuildRequires:  ffmpeg-free-devel
BuildRequires:  portaudio-devel

# Runtime system dependencies
Requires:       wl-clipboard
Requires:       ydotool >= 1.0
Requires:       ffmpeg-free
Requires:       portaudio
Requires:       python3 >= 3.13

# Disable automatic Python dependency generation - we bundle everything
%{?python_disable_dependency_generator}

%description
Voice-to-text for Linux using Whisper AI. Press a keyboard shortcut, speak,
release to paste. Supports both CLI and GUI modes with Qt6 system tray
integration.

%prep
%autosetup -n %{pypi_name_underscore}-%{version}

%generate_buildrequires
# Only generate build requirements, skip runtime dependencies (-R)
# We'll bundle all Python deps from PyPI since many aren't in Fedora repos
%pyproject_buildrequires -R

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files talk_it_out

# Install ALL Python dependencies from PyPI (bundle into RPM)
# This creates a self-contained RPM with no Python package dependencies
%{__python3} -m pip install --target %{buildroot}%{python3_sitelib} \
    --upgrade --ignore-installed \
    'typer>=0.9.0' \
    'structlog>=24.0.0' \
    'tomli-w>=1.0.0' \
    'evdev>=1.6.0' \
    'numpy' \
    'sounddevice>=0.5.3' \
    'scipy' \
    'faster-whisper>=1.2.0' \
    'pyqt6>=6.10.0'

# Install .desktop file
install -D -m 0644 packaging/common/talk-it-out.desktop \
    %{buildroot}%{_datadir}/applications/talk-it-out.desktop

%check
%pyproject_check_import

%files -f %{pyproject_files}
%license LICENSE
%doc README.md
%{_bindir}/talk-it-out
%{_datadir}/applications/talk-it-out.desktop

%changelog
* Sun Jan 26 2025 Ed Ropple <ed@edropple.com> - 0.1.0-1
- Initial RPM release
- CLI and GUI modes for voice-to-text transcription
- Whisper AI integration with GPU acceleration support
- Wayland native with wl-clipboard and ydotool
