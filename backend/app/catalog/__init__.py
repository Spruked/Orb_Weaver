"""Commercial catalog intelligence for ORB Weaver."""

from . import compiler as _compiler
from .compiler_v2 import install_catalog_v2

install_catalog_v2(_compiler)

compile_commercial_catalog = _compiler.compile_commercial_catalog

__all__ = ["compile_commercial_catalog"]
