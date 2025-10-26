# pattern: Functional Core
# Public API exports for output package

from .base import OutputStrategy, OutputError
from .factory import create_output_strategy

__all__ = [
    "OutputStrategy",
    "OutputError",
    "create_output_strategy",
]
