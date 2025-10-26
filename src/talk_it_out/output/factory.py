# pattern: Functional Core
# Pure factory function for strategy selection

from .base import OutputStrategy


def create_output_strategy(config: dict) -> OutputStrategy:
    """Create output strategy from config.

    Args:
        config: Full config dict with [output] section

    Returns:
        OutputStrategy instance configured from config

    Raises:
        ValueError: If strategy name unknown
    """
    strategy_name = config["output"]["strategy"]

    if strategy_name == "wl-clip-simplepaste":
        # Lazy import to avoid loading strategies not in use
        from .strategies.wl_clip import WlClipSimplePaste
        wl_clip_config = config["output"].get("wl-clip", {})
        return WlClipSimplePaste(wl_clip_config)
    else:
        valid_strategies = ["wl-clip-simplepaste"]
        raise ValueError(
            f"Unknown output strategy: '{strategy_name}'. "
            f"Valid strategies: {', '.join(valid_strategies)}"
        )
