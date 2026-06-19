"""med2limit MED/RMED to LIMIT converter for Code_Aster shell and solid models."""

from importlib.metadata import PackageNotFoundError, version

from .converter import MEDToLimitConverter
from .cli import main

try:
    __version__ = version("med2limit")
except PackageNotFoundError:  # paquet pas installé (exécution depuis les sources)
    __version__ = "0.0.0"

__all__ = ["MEDToLimitConverter", "main"]
