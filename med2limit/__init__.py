"""med2limit — MED/RMED to LIMIT converter for Code_Aster shell and solid models."""

from .converter import MEDToLimitConverter
from .cli import main

__version__ = "0.10.0"
__all__ = ["MEDToLimitConverter", "main"]
