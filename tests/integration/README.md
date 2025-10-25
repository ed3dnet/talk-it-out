# Integration Tests

Integration tests verify end-to-end behavior of the CLI application.

## Running Tests

```bash
bash tests/integration/test_cli_framework.sh
```

Or from project root:
```bash
./tests/integration/test_cli_framework.sh
```

## Test Suite

### Framework Tests (1-5)

1. **Fresh install config creation** - Verifies default config is created
2. **Invalid config detection** - Tests config validation errors
3. **Custom config path** - Tests --config flag
4. **Log level override** - Tests --log-level flag
5. **SIGTERM handling** - Verifies graceful shutdown

### Keyboard Monitoring Tests (6-9)

6. **Keyboard monitoring startup** - Verifies monitoring initializes
7. **Invalid combo key detection** - Tests key name validation
8. **Empty combos dict validation** - Tests empty combos are rejected
9. **Keyboard monitoring cleanup** - Verifies clean shutdown

## Test Structure

Each test:
1. Sets up test environment (cleans config, creates test files)
2. Runs application with specific configuration
3. Verifies expected behavior (logs, exit codes, files)
4. Cleans up test artifacts

## Cleanup

Tests use `trap cleanup EXIT` to ensure cleanup runs regardless of test outcome.

Cleaned resources:
- `~/.config/talk-it-out` directory
- `/tmp/test-config.toml`
- `/tmp/test*-output.txt` files

## Exit Codes

- **0**: All tests passed
- **1**: One or more tests failed

## Requirements

- User in `input` group (for keyboard monitoring tests)
- `uv` package manager installed
- Project dependencies installed (`uv sync`)
