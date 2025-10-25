# Agent Development Conventions

This file provides guidance for AI agents working on this codebase.

## Testing Guidelines

**NEVER modify user's global config during tests.**

All tests that need custom configuration MUST:
- Use the `--config` / `-c` flag to specify a test-specific config file
- Create temporary config files (e.g., `/tmp/test-config.toml`)
- Clean up test config files after tests complete
- NEVER write to `~/.config/talk-it-out/config.toml` during automated tests

**Example:**
```bash
# Good - uses temporary config
cat > /tmp/test-config.toml << EOF
[keys.combos]
test = [["KEY_A"]]
EOF
uv run python -m talk_it_out.main run --config /tmp/test-config.toml

# Bad - modifies user's global config
echo "test" > ~/.config/talk-it-out/config.toml  # DON'T DO THIS
```

## Dependency Management

**Use `uv` for all dependency operations:**

### Adding Dependencies

**Runtime dependencies:**
```bash
# Add to [project.dependencies] in pyproject.toml
uv add typer structlog
```

**Development dependencies:**
```bash
# Add to [dependency-groups.dev] in pyproject.toml
uv add --dev pytest ruff mypy
```

**Manual approach (if uv add not available):**
1. Edit `pyproject.toml` directly
2. Add to `[project.dependencies]` or `[dependency-groups.dev]`
3. Run `uv sync` to install

**Never:**
- Use `pip install` directly
- Use `source .venv/bin/activate` in scripts
- Forget to update pyproject.toml

### Running Commands

**Always use `uv run` to execute commands in the project environment:**

```bash
# Run tests
uv run pytest tests/

# Run application
uv run python -m talk_it_out.main

# Run any command with project dependencies
uv run mypy src/
```

**Why `uv run`:**
- Automatically uses the project's virtual environment
- No need to activate/deactivate
- Works in any shell context
- Ensures reproducible execution

### Syncing Dependencies

After modifying `pyproject.toml`:
```bash
uv sync
```

This installs all dependencies (runtime + dev groups).

## Testing

**Always use `uv run pytest`:**

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/framework/test_config.py

# Run with verbose output
uv run pytest -v

# Run specific test
uv run pytest tests/framework/test_config.py::test_name -v
```

## Common Tasks

**Install project in development mode:**
```bash
uv sync
```

**Add a new runtime dependency:**
```bash
# Preferred: use uv add
uv add package-name

# Alternative: edit pyproject.toml + sync
# 1. Add to [project.dependencies]
# 2. Run: uv sync
```

**Add a new dev dependency:**
```bash
# Preferred: use uv add
uv add --dev package-name

# Alternative: edit pyproject.toml + sync
# 1. Add to [dependency-groups.dev]
# 2. Run: uv sync
```

**Run the application:**
```bash
uv run python -m talk_it_out.main run
```

**Format code:**
```bash
uv run ruff format src/ tests/
```

## TDD Workflow

1. Write test (it should fail)
   ```bash
   uv run pytest tests/framework/test_config.py -v
   ```

2. Implement code to make test pass

3. Run test again (should pass)
   ```bash
   uv run pytest tests/framework/test_config.py -v
   ```

4. Commit both test and implementation

## Summary

- **Use `uv run` for all commands** - never activate virtualenv manually
- **Update `pyproject.toml` first** - then `uv sync` to install
- **Runtime deps** → `[project.dependencies]`
- **Dev deps** → `[dependency-groups.dev]`
- **Tests** → `uv run pytest`
