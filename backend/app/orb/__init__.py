"""Local-first ORB runtime helpers."""

from . import pointer_plot as _pointer_plot
from .execution_clamp import clamp_orb_execution
from .pointer_recovery_integration import install_pointer_recovery_optimizer
from .pointer_truth import install_pointer_truth_policy
from .topology import SemanticTopologyScraper, scan_semantic_topology

# Truth policy must be installed before crawler modules consume pointer extraction.
install_pointer_truth_policy(_pointer_plot)
install_pointer_recovery_optimizer()

__all__ = [
    "SemanticTopologyScraper",
    "clamp_orb_execution",
    "scan_semantic_topology",
]
