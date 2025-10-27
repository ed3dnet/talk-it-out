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

# Note: Not noarch because we bundle PyQt6 which has compiled extensions
# BuildArch:      noarch

# Build dependencies
BuildRequires:  python3-devel >= 3.13
BuildRequires:  python3-build
BuildRequires:  python3-pip
BuildRequires:  python3-setuptools
BuildRequires:  pyproject-rpm-macros

# System library build dependencies
BuildRequires:  ffmpeg-free-devel
BuildRequires:  portaudio-devel

# Python dependencies available as Fedora RPMs (build and runtime)
BuildRequires:  python3dist(typer) >= 0.9
BuildRequires:  python3dist(tomli-w) >= 1
BuildRequires:  python3dist(evdev) >= 1.6
BuildRequires:  python3dist(numpy)
BuildRequires:  python3dist(scipy)
# Note: PyQt6 6.10+ not in Fedora (has 6.9), will bundle from PyPI

# Runtime system dependencies
Requires:       wl-clipboard
Requires:       ydotool >= 1.0
Requires:       ffmpeg-free
Requires:       portaudio
Requires:       python3 >= 3.13

# Runtime Python dependencies (from Fedora RPMs)
Requires:       python3dist(typer) >= 0.9
Requires:       python3dist(tomli-w) >= 1
Requires:       python3dist(evdev) >= 1.6
Requires:       python3dist(numpy)
Requires:       python3dist(scipy)
# Note: PyQt6 6.10+ bundled from PyPI (Fedora has 6.9)

# Disable automatic Python dependency generation
# We manually specify deps above + bundle some from PyPI
%{?python_disable_dependency_generator}

# Disable build-id generation - bundled PyPI wheels don't have build-ids
%global _missing_build_ids_terminate_build 0
# Disable debuginfo generation - bundled wheels are precompiled
%global debug_package %{nil}

%description
Voice-to-text for Linux using Whisper AI. Press a keyboard shortcut, speak,
release to paste. Supports both CLI and GUI modes with Qt6 system tray
integration.

%prep
%autosetup -n %{pypi_name_underscore}-%{version}

%generate_buildrequires
# Generate build requirements only (no runtime dependencies with -R)
# Python package deps are manually specified in BuildRequires above
%pyproject_buildrequires -R

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files talk_it_out

# Bundle dependencies not available as Fedora RPMs (or wrong version)
# Others are satisfied by BuildRequires above
%{__python3} -m pip install --target %{buildroot}%{python3_sitelib} \
    --upgrade --ignore-installed \
    'structlog>=24.0.0' \
    'sounddevice>=0.5.3' \
    'faster-whisper>=1.2.0' \
    'pyqt6>=6.10.0'

# Install .desktop file
install -D -m 0644 packaging/common/talk-it-out.desktop \
    %{buildroot}%{_datadir}/applications/talk-it-out.desktop

%check
# Skip import check - bundled dependencies aren't in PYTHONPATH during check phase
# The package will be tested during CI/CD pipeline instead
# %pyproject_check_import

%files
%license LICENSE
%doc README.md
%{_bindir}/talk-it-out
%{_datadir}/applications/talk-it-out.desktop
# All Python files (our package + bundled dependencies)
%{python3_sitelib}/*

%changelog
* Sun Jan 26 2025 Ed Ropple <ed@edropple.com> - 0.1.0-1
- Initial RPM release
- CLI and GUI modes for voice-to-text transcription
- Whisper AI integration with GPU acceleration support
- Wayland native with wl-clipboard and ydotool
