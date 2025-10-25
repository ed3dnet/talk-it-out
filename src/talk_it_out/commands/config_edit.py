# pattern: Imperative Shell
# Handles config editing with external editor and validation

import os
import sys
import subprocess
import typer

from talk_it_out.framework import config, config_io


def edit_config() -> int:
    """Edit config in $EDITOR, validate on exit.

    Why this exists: Provides interactive config editing with validation.
    Creates default config if it doesn't exist, then opens in user's
    preferred editor.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    config_path = config.get_config_path()

    # Create default config if doesn't exist
    if not config_path.exists():
        cfg = config.default_config()
        config_io.save_config(config_path, cfg)
        print(f"✅ Created default config at {config_path}")

    # Get editor from environment
    editor = os.environ.get("EDITOR", "nano")

    # Launch editor
    result = subprocess.run([editor, str(config_path)])
    if result.returncode != 0:
        print(f"❌ Editor exited with error code {result.returncode}", file=sys.stderr)
        return result.returncode

    # Validate edited config
    try:
        cfg = config_io.load_config(config_path)
        errors = config.validate_config(cfg)

        if errors:
            print("❌ Config validation failed:", file=sys.stderr)
            for error in errors:
                print(f"  • {error}", file=sys.stderr)

            # Ask to re-edit
            if typer.confirm("Edit again?"):
                return edit_config()  # Recursive retry
            return 1

        print("✅ Config validated successfully")
        return 0

    except ValueError as e:
        print(f"❌ Error loading config: {e}", file=sys.stderr)
        if typer.confirm("Edit again?"):
            return edit_config()
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1
