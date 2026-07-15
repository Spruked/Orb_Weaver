"""
Deprecated Gate 1 shim.

ACP is no longer the active Gate 1 design. Use:
tpc_core.axis1_input_trinity.input_gateway.faster_whisper_gateway
"""

from Orb_Assistant.tpc_website_orb.tpc_core.axis1_input_trinity.input_gateway.faster_whisper_gateway import (
    FasterWhisperInputGateway,
    Gate1Stimulus,
    get_input_gateway,
)


ACPInterface = FasterWhisperInputGateway
EpistemicStimulus = Gate1Stimulus


def get_acp(*args, **kwargs):
    """Deprecated compatibility shim. Use get_input_gateway()."""
    return get_input_gateway(*args, **kwargs)
