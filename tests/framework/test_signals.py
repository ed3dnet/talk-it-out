# pattern: Functional Core tests
# Tests for signal handling and cleanup

import time
from talk_it_out.framework import signals


def test_cleanup_registry_can_register_functions():
    """Should be able to register cleanup functions"""
    registry = signals.CleanupRegistry()

    def cleanup():
        pass

    registry.register(cleanup)

    assert len(registry.cleanup_fns) == 1


def test_cleanup_registry_runs_all_functions():
    """run_all should execute all registered functions"""
    registry = signals.CleanupRegistry()

    counter = {"value": 0}

    def cleanup1():
        counter["value"] += 1

    def cleanup2():
        counter["value"] += 10

    registry.register(cleanup1)
    registry.register(cleanup2)
    registry.run_all(timeout=1.0)

    assert counter["value"] == 11


def test_cleanup_registry_respects_timeout():
    """run_all should timeout if cleanup takes too long"""
    registry = signals.CleanupRegistry()

    def slow_cleanup():
        time.sleep(5)  # Intentionally slow

    registry.register(slow_cleanup)

    # Should not hang - should timeout
    start = time.time()
    registry.run_all(timeout=1.0)
    elapsed = time.time() - start

    # Should have timed out around 1 second, not waited 5
    assert elapsed < 2.0


def test_cleanup_method_uses_default_timeout():
    """cleanup() should call run_all with default timeout"""
    registry = signals.CleanupRegistry()

    counter = {"value": 0}

    def cleanup1():
        counter["value"] += 1

    registry.register(cleanup1)
    registry.cleanup()  # Should use default timeout of 3.0

    assert counter["value"] == 1
