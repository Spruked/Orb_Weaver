"""Factory import boundary for the dependency-free Web-TAMP package.

This bridge intentionally does not execute planning or authorization. It makes
the canonical contracts available to factory modules without moving them into
the factory application package.
"""

from web_tamp_contracts import *  # noqa: F401,F403
