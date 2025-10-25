#!/bin/bash
# Integration tests for CLI framework
# Tests end-to-end scenarios with real config, logging, and signal handling

set -e  # Exit on error

echo "=== CLI Framework Integration Tests ==="
echo ""

# Cleanup function
cleanup() {
    echo "Cleaning up test artifacts..."
    rm -rf ~/.config/talk-it-out-test
    rm -f /tmp/test-config.toml
}

# Run cleanup on exit
trap cleanup EXIT

echo "Test 1: Fresh install - default config creation"
rm -rf ~/.config/talk-it-out
uv run python -m talk_it_out.main run --log-level INFO &
PID=$!
sleep 2
kill -INT $PID
wait $PID && EXIT_CODE=0 || EXIT_CODE=$?

if [ -f ~/.config/talk-it-out/config.toml ]; then
    echo "✅ Test 1 passed: Default config created"
else
    echo "❌ Test 1 failed: Default config not created"
    exit 1
fi

if [ $EXIT_CODE -eq 130 ]; then
    echo "✅ Test 1 passed: Correct exit code (130) on SIGINT"
else
    echo "❌ Test 1 failed: Expected exit code 130, got $EXIT_CODE"
    exit 1
fi

echo ""
echo "Test 2: Invalid config - validation error"
echo "[whisper]" >> ~/.config/talk-it-out/config.toml
echo 'model = "invalid"' >> ~/.config/talk-it-out/config.toml

if uv run python -m talk_it_out.main run 2>&1 | grep -q "Configuration error"; then
    echo "✅ Test 2 passed: Invalid config detected"
else
    echo "❌ Test 2 failed: Invalid config not detected"
    exit 1
fi

echo ""
echo "Test 3: Custom config path"
rm -f /tmp/test-config.toml
uv run python -m talk_it_out.main run --config /tmp/test-config.toml --log-level DEBUG &
PID=$!
sleep 2
kill -INT $PID
wait $PID || true

if [ -f /tmp/test-config.toml ]; then
    echo "✅ Test 3 passed: Custom config path works"
else
    echo "❌ Test 3 failed: Custom config not created"
    exit 1
fi

echo ""
echo "Test 4: Log level override"
rm -rf ~/.config/talk-it-out
rm -f /tmp/test4-output.txt
timeout 3 uv run python -m talk_it_out.main run --log-level DEBUG > /tmp/test4-output.txt 2>&1 || true

if grep -qi "debug" /tmp/test4-output.txt; then
    echo "✅ Test 4 passed: Log level override works"
else
    echo "❌ Test 4 failed: Debug logs not shown"
    cat /tmp/test4-output.txt
    exit 1
fi
rm -f /tmp/test4-output.txt

echo ""
echo "Test 5: SIGTERM handling"
rm -rf ~/.config/talk-it-out
uv run python -m talk_it_out.main run &
PID=$!
sleep 2
kill -TERM $PID
wait $PID && EXIT_CODE=0 || EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Test 5 passed: Correct exit code (0) on SIGTERM"
else
    echo "❌ Test 5 failed: Expected exit code 0, got $EXIT_CODE"
    exit 1
fi

echo ""
echo "Test 6: Keyboard monitoring starts successfully"
rm -rf ~/.config/talk-it-out
rm -f /tmp/test6-output.txt
timeout 3 uv run python -m talk_it_out.main run --log-level INFO > /tmp/test6-output.txt 2>&1 || true

# Check for keyboard monitoring startup log
if grep -q "keyboard_monitoring_started" /tmp/test6-output.txt; then
    echo "✅ Test 6 passed: Keyboard monitoring started"
else
    echo "❌ Test 6 failed: No keyboard monitoring startup log found"
    cat /tmp/test6-output.txt
    exit 1
fi
rm /tmp/test6-output.txt

echo ""
echo "Test 7: Invalid combo key name detection"
rm -rf ~/.config/talk-it-out
mkdir -p ~/.config/talk-it-out

# Create config with invalid key name in combo (using new format)
cat > ~/.config/talk-it-out/config.toml << 'EOF'
[keys.combos]
test_combo = [["KEY_INVALID"]]

[audio]
sample_rate = 16000
channels = 1
device = ""

[whisper]
model = "base"
language = ""

[paste]
method = "clipboard"

[logging]
level = "INFO"
EOF

# Run and expect validation error
if uv run python -m talk_it_out.main run 2>&1 | grep -q "Invalid key name 'KEY_INVALID'"; then
    echo "✅ Test 7 passed: Invalid combo key detected"
else
    echo "❌ Test 7 failed: Invalid key validation did not trigger"
    exit 1
fi

echo ""
echo "Test 8: Empty combos dict validation"
rm -rf ~/.config/talk-it-out
mkdir -p ~/.config/talk-it-out

# Create config with empty combos
cat > ~/.config/talk-it-out/config.toml << 'EOF'
[keys.combos]

[audio]
sample_rate = 16000
channels = 1
device = ""

[whisper]
model = "base"
language = ""

[paste]
method = "clipboard"

[logging]
level = "INFO"
EOF

# Run and expect validation error
if uv run python -m talk_it_out.main run 2>&1 | grep -q "combos cannot be empty"; then
    echo "✅ Test 8 passed: Empty combos dict detected"
else
    echo "❌ Test 8 failed: Empty combos validation did not trigger"
    exit 1
fi

echo ""
echo "Test 9: Keyboard monitoring cleanup on shutdown"
rm -rf ~/.config/talk-it-out
rm -f /tmp/test9-output.txt
uv run python -m talk_it_out.main run --log-level INFO > /tmp/test9-output.txt 2>&1 &
PID=$!
sleep 2
kill -INT $PID
wait $PID || true

# Check for clean shutdown logs
if grep -q "keyboard_monitor_stopping" /tmp/test9-output.txt && \
   grep -q "keyboard_monitor_stopped" /tmp/test9-output.txt && \
   grep -q "shutdown_complete" /tmp/test9-output.txt; then
    echo "✅ Test 9 passed: Keyboard monitoring cleanup successful"
else
    echo "❌ Test 9 failed: Missing cleanup logs"
    cat /tmp/test9-output.txt
    exit 1
fi
rm /tmp/test9-output.txt

echo ""
echo "=== All integration tests passed! (9 tests) ==="
