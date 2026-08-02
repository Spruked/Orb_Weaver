"""Stage Governor service — action validation, stage lifecycle"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models import ToolEntry

STAGE_LIFECYCLE = [
    "preflight",
    "crawl",
    "assessment",
    "presentation",
    "package_generation",
    "checkout",
    "confirmation",
    "installation",
    "verification",
    "closure"
]

CONSEQUENTIAL_ACTIONS = {
    "payment", "signature", "checkout", "package_generation",
    "installation", "launch_verification", "destructive_control"
}

class StageGovernor:
    def __init__(self):
        self.allowed_actions_per_stage = self._default_actions()

    def _default_actions(self) -> Dict[str, List[str]]:
        return {
            "preflight": ["greet", "introduce", "site_world", "pointer_plot"],
            "crawl": ["site_world", "page_capsule", "ask_question", "clarify"],
            "assessment": ["roi_calculator", "ask_question", "page_capsule", "pointer_plot"],
            "presentation": ["roi_calculator", "page_capsule", "pointer_plot", "forms"],
            "package_generation": ["generate_package", "forms", "booking"],
            "checkout": ["checkout", "forms"],
            "confirmation": ["confirm", "signature"],
            "installation": ["install", "verify_install"],
            "verification": ["verify_install", "test_run"],
            "closure": ["support_handoff", "crm", "farewell"],
        }

    def validate_action(self, stage: str, action: str, tool: ToolEntry) -> Dict[str, Any]:
        """Returns validation result with approval requirements."""
        allowed = self.allowed_actions_per_stage.get(stage, [])
        is_allowed = action in allowed and tool.enabled
        requires_confirmation = action in CONSEQUENTIAL_ACTIONS or tool.requires_approval

        return {
            "allowed": is_allowed,
            "requires_visitor_confirmation": requires_confirmation,
            "requires_owner_approval": tool.requires_approval and action in CONSEQUENTIAL_ACTIONS,
            "stage": stage,
            "action": action,
            "tool_id": tool.id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_stage_tools(self, stage: str, tools: List[ToolEntry]) -> List[Dict[str, Any]]:
        allowed = self.allowed_actions_per_stage.get(stage, [])
        result = []
        for tool in tools:
            if tool.enabled and any(a in allowed for a in [tool.id, tool.category]):
                result.append({
                    "tool": tool,
                    "available": True,
                    "requires_confirmation": tool.id in CONSEQUENTIAL_ACTIONS or tool.requires_approval,
                })
        return result

    def transition_stage(self, current: str, next_stage: str) -> Dict[str, Any]:
        if next_stage not in STAGE_LIFECYCLE:
            return {"valid": False, "error": f"Unknown stage: {next_stage}"}

        current_idx = STAGE_LIFECYCLE.index(current) if current in STAGE_LIFECYCLE else -1
        next_idx = STAGE_LIFECYCLE.index(next_stage)

        # Allow forward, backward, or same stage
        return {
            "valid": True,
            "from": current,
            "to": next_stage,
            "direction": "forward" if next_idx > current_idx else "backward" if next_idx < current_idx else "same",
            "timestamp": datetime.utcnow().isoformat(),
        }

stage_governor = StageGovernor()
