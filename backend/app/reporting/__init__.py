"""Audit narrative and report compilation."""

from . import audit_reporting as _audit_reporting
from .truth_adapter import install_reporting_truth_adapter

install_reporting_truth_adapter(_audit_reporting)
