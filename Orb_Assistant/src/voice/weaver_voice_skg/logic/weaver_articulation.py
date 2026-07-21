"""
weaver_articulation.py
======================
Core logic for the Weaver Voice & Personality SKG.

Deterministic tone selection, evidence-bound humor, first-person enforcement,
and anti-decoration compliance. No tribunal. No convergence. Stage Governor
provides canonical state; this module selects and renders the voice envelope.

Entry Points (per worker.json):
  - articulate(context) → WeaverResponse
  - evaluate_tone(stage_id, evidence) → ToneEvaluation
  - generate_response(envelope) → str

Architecture:
  Stage Governor Snapshot
    ↓
  Stage ID lookup → Humor Level + Preset
    ↓
  Evidence validation (humor_requires_evidence)
    ↓
  First-person enforcement
    ↓
  Anti-decoration check (stabilization_threshold_ms)
    ↓
  Rendered response

Author: ORBS Architecture Team
Version: 1.0.0
"""

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class HumorLevel(Enum):
    FULL = "full"
    FOCUSED = "focused"
    QUIET = "quiet"
    CELEBRATORY = "celebratory"


class InitiativeLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class WeaverResponse:
    """Standard output envelope for all Weaver articulation."""
    text: str
    humor_level: HumorLevel
    initiative: InitiativeLevel
    evidence_bound: bool
    first_person_compliant: bool
    anti_decoration_compliant: bool
    stage_id: str
    recommended_action: Optional[str] = None
    handoff_triggered: bool = False
    prohibited_patterns_detected: List[str] = field(default_factory=list)


@dataclass
class ToneEvaluation:
    """Result of tone evaluation for a given stage + evidence."""
    humor_level: HumorLevel
    preset_name: str
    initiative: InitiativeLevel
    can_joke: bool
    can_initiate: bool
    stabilization_delay_ms: int
    entry_guidance_required: bool


class WeaverArticulation:
    """
    Deterministic voice personality engine for ORBS.

    No LLM creativity. No tribunal convergence. Stage state drives tone.
    Evidence drives humor. First person is mandatory. Anti-decoration is enforced.
    """

    def __init__(self, skg_root: str = "."):
        self.skg_root = skg_root
        self._load_contracts()
        self._load_presets()
        self._load_mappings()
        self._load_cognitive_state()

        # Runtime state removed from the articulation instance
        # All request-specific state is supplied via context

    # ── Loading ────────────────────────────────────────────────

    def _load_contracts(self):
        path = os.path.join(self.skg_root, "worker.json")
        with open(path, "r") as f:
            self.contract = json.load(f)
        self.governance = self.contract["governance"]
        self.anti_decoration = self.contract["anti_decoration_rule"]

    def _load_presets(self):
        self.presets = {}
        preset_dir = os.path.join(self.skg_root, "voice_presets")
        for fname in os.listdir(preset_dir):
            if fname.endswith(".json"):
                with open(os.path.join(preset_dir, fname), "r") as f:
                    data = json.load(f)
                    self.presets[data["preset_name"]] = data

    def _load_mappings(self):
        path = os.path.join(self.skg_root, "stage_mappings", "stage_to_humor_level.json")
        with open(path, "r") as f:
            self.mappings = json.load(f)

    def _load_cognitive_state(self):
        import yaml
        path = os.path.join(self.skg_root, "cognitive_state", "weaver_cognitive_state.yaml")
        with open(path, "r") as f:
            self.cognitive = yaml.safe_load(f)

    # ── Public API ─────────────────────────────────────────────

    def articulate(self, context: Dict[str, Any]) -> WeaverResponse:
        """
        Main entry point. Receives a full situational envelope and returns
        a rendered Weaver response with all compliance flags.

        Context envelope (required keys):
          - stage_id: str                    # From Stage Governor
          - screen_stable_at: float          # Unix timestamp when UI stabilized
          - visitor_input_active: bool       # Is user currently typing/speaking?
          - evidence: Dict[str, Any]         # Sanitized scan/audit findings
          - visitor_statement: Optional[str] # Raw visitor input
          - allowed_actions: List[str]       # Governor-approved actions
          - recommended_action: Optional[str]# Highest-ranked approved action
          - situation_description: str       # Human-readable situation
        """
        stage_id = context.get("stage_id", "unknown")
        evidence = context.get("evidence", {})
        visitor_statement = context.get("visitor_statement", "")
        intent_result = context.get("intent_result")
        allowed_actions = context.get("allowed_actions", [])
        recommended_action = context.get("recommended_action")
        screen_stable_at = context.get("screen_stable_at", time.time())
        visitor_input_active = context.get("visitor_input_active", False)
        situation = context.get("situation_description", "")

        # 1. Evaluate tone for this stage
        tone = self.evaluate_tone(stage_id, evidence)

        # 2. Check anti-decoration compliance
        anti_decoration_ok = self._check_anti_decoration(
            screen_stable_at, visitor_input_active, stage_id
        )

        # 3. If visitor is actively inputting → hand off, do not interrupt
        if visitor_input_active:
            return self._handoff_response(stage_id, tone)

        # 4. Process visitor statement if present only when verified SF-ORB intent is present
        if visitor_statement:
            if not isinstance(intent_result, dict) or intent_result.get("source") != "sf_orb" or intent_result.get("status") != "classified":
                return self._safe_deferred_response(stage_id, tone)

            return self._handle_visitor_input(
                visitor_statement=visitor_statement,
                intent_result=intent_result,
                allowed_actions=allowed_actions,
                recommended_action=recommended_action,
                stage_id=stage_id,
                tone=tone,
                evidence=evidence,
            )

        # 5. Generate situational response
        text = self._generate_situational_response(
            stage_id, tone, evidence, situation, recommended_action
        )

        # 6. Enforce first person
        text, fp_compliant = self._enforce_first_person(text)
        if self._contains_first_person(text):
            fp_compliant = True

        # 7. Check for prohibited patterns
        prohibited = self._detect_prohibited_patterns(text, tone)

        # 8. Evidence-bound check
        evidence_bound = self._check_evidence_bound(text, evidence, tone)

        return WeaverResponse(
            text=text,
            humor_level=tone.humor_level,
            initiative=tone.initiative,
            evidence_bound=evidence_bound,
            first_person_compliant=fp_compliant,
            anti_decoration_compliant=anti_decoration_ok,
            stage_id=stage_id,
            recommended_action=recommended_action,
            handoff_triggered=False,
            prohibited_patterns_detected=prohibited
        )

    def evaluate_tone(self, stage_id: str, evidence: Dict[str, Any]) -> ToneEvaluation:
        """
        Given a stage ID and available evidence, return the exact tone envelope.
        No reasoning. No convergence. Direct lookup + evidence gate.
        """
        mapping = self.mappings["mappings"].get(stage_id)
        if not mapping:
            # Fallback to focused if stage unknown
            mapping = {
                "humor_level": "focused",
                "preset_file": "voice_presets/focused_warmth.json",
                "initiative": "medium",
                "entry_guidance_required": True,
                "stabilization_delay_ms": 2500
            }

        humor_level = HumorLevel(mapping["humor_level"])
        preset_name = os.path.basename(mapping["preset_file"]).replace(".json", "")
        initiative = InitiativeLevel(mapping["initiative"])

        # Evidence gate: if humor requires evidence and no evidence is provided,
        # humor is suppressed. Full and celebratory tones downgrade to focused;
        # focused and quiet remain in their own lane.
        can_joke = humor_level != HumorLevel.QUIET
        if self.governance["humor_requires_evidence"]:
            if not evidence or len(evidence) == 0:
                can_joke = False
                if humor_level == HumorLevel.FULL:
                    humor_level = HumorLevel.FOCUSED
                elif humor_level == HumorLevel.CELEBRATORY:
                    humor_level = HumorLevel.FOCUSED

        return ToneEvaluation(
            humor_level=humor_level,
            preset_name=preset_name,
            initiative=initiative,
            can_joke=can_joke,
            can_initiate=humor_level != HumorLevel.QUIET and mapping.get("initiative") in {"high", "medium"},
            stabilization_delay_ms=mapping["stabilization_delay_ms"],
            entry_guidance_required=mapping["entry_guidance_required"]
        )

    def generate_response(self, envelope: Dict[str, Any]) -> str:
        """
        Lower-level entry point. Accepts a minimal envelope and returns raw text.
        Used when the caller already knows the tone and just needs rendering.
        """
        stage_id = envelope.get("stage_id", "unknown")
        evidence = envelope.get("evidence", {})
        situation = envelope.get("situation", "")
        tone = self.evaluate_tone(stage_id, evidence)
        text = self._generate_situational_response(stage_id, tone, evidence, situation, None)
        text, _ = self._enforce_first_person(text)
        return text

    # ── Internal Logic ─────────────────────────────────────────

    def _check_anti_decoration(self, screen_stable_at: float, 
                                visitor_input_active: bool,
                                stage_id: str) -> bool:
        """
        Anti-decoration rule: After stabilization, Weaver must deliver
        guidance OR hand off within stabilization_threshold_ms.
        """
        if visitor_input_active:
            return True  # User speaking — Weaver correctly silent

        threshold_ms = self.anti_decoration["stabilization_threshold_ms"]
        elapsed_ms = (time.time() - screen_stable_at) * 1000

        if elapsed_ms > threshold_ms:
            # After the threshold has passed without a handoff, the screen is non-compliant.
            return False

        return True  # Still within stabilization window

    def _handoff_response(self, stage_id: str, tone: ToneEvaluation) -> WeaverResponse:
        """Generate a handoff response when user is actively inputting."""
        handoff_phrases = self.cognitive["anti_decoration_state"]["handoff_phrases"]
        text = handoff_phrases[0]  # Default handoff

        return WeaverResponse(
            text=text,
            humor_level=tone.humor_level,
            initiative=InitiativeLevel.LOW,
            evidence_bound=True,
            first_person_compliant=True,
            anti_decoration_compliant=True,
            stage_id=stage_id,
            handoff_triggered=True
        )

    def _handle_visitor_input(self, visitor_statement: str, intent_result: Dict[str, Any],
                              allowed_actions: List[str], recommended_action: Optional[str],
                              stage_id: str, tone: ToneEvaluation, evidence: Dict) -> WeaverResponse:
        """
        Intent interpretation → Governor-approved action validation.
        Weaver understands freely. He routes ONLY to approved actions.
        """
        normalized_intent = self._normalize_intent(visitor_statement, stage_id, intent_result)

        # Check if recommended action is in allowed_actions
        action_valid = recommended_action in allowed_actions if recommended_action else False

        if not action_valid and recommended_action:
            # Action not approved — constrained fallback
            available = allowed_actions[0] if allowed_actions else None
            text = (
                f"I understand what you're trying to do, but that step is not available "
                f"from here yet. The next available step is {available or 'to continue browsing'}. "
                f"Here's why that makes sense right now."
            )
        elif normalized_intent == "ambiguous":
            text = (
                "I want to make sure I point you in exactly the right direction. "
                "Could you tell me a bit more about what you're looking for?"
            )
        elif normalized_intent == "no_match":
            text = (
                "I'm not sure I caught that correctly. I can help with scanning your site, "
                "reviewing your audit, or walking you through the next steps. What would be most useful?"
            )
        else:
            # Valid intent + valid action
            text = self._generate_guidance_for_action(
                recommended_action, stage_id, tone, evidence
            )

        text, fp_compliant = self._enforce_first_person(text)
        prohibited = self._detect_prohibited_patterns(text, tone)
        evidence_bound = self._check_evidence_bound(text, evidence, tone)

        return WeaverResponse(
            text=text,
            humor_level=tone.humor_level,
            initiative=tone.initiative,
            evidence_bound=evidence_bound,
            first_person_compliant=fp_compliant,
            anti_decoration_compliant=True,
            stage_id=stage_id,
            recommended_action=recommended_action,
            prohibited_patterns_detected=prohibited
        )

    def _normalize_intent(self, statement: str, stage_id: str, intent_result: Optional[Dict[str, Any]] = None) -> str:
        """
        Normalize visitor statement to intent category.
        Verified SF-ORB intent is required before the local fallback is used.
        """
        if not isinstance(intent_result, dict):
            return "deferred"
        if intent_result.get("source") != "sf_orb" or intent_result.get("status") != "classified":
            return "deferred"

        statement_lower = statement.lower()

        # Check stage-specific routing table
        stage_intents = self.mappings.get("intent_routing_table", {}).get(stage_id, {})
        for phrase, route in stage_intents.items():
            if phrase.lower() in statement_lower:
                return route["intent"]

        # Global fallback patterns
        if any(w in statement_lower for w in ["scan", "check", "audit", "look at"]):
            return "preflight_interest"
        if any(w in statement_lower for w in ["cost", "price", "how much", "package"]):
            return "package_exploration"
        if any(w in statement_lower for w in ["demo", "show", "see", "what does"]):
            return "product_demonstration"
        if any(w in statement_lower for w in ["account", "login", "sign in", "already have"]):
            return "returning_customer"
        if any(w in statement_lower for w in ["invest", "investor", "fund", "back"]):
            return "investor_interest"
        if any(w in statement_lower for w in ["look", "browse", "just", "around"]):
            return "exploration"

        return "ambiguous"

    def _safe_deferred_response(self, stage_id: str, tone: ToneEvaluation) -> WeaverResponse:
        """Return a safe deferred response when verified SF-ORB intent is missing."""
        text = (
            "I’m holding this for verified intent routing. "
            "I need the SF-ORB classification before I can guide you safely."
        )
        return WeaverResponse(
            text=text,
            humor_level=tone.humor_level,
            initiative=InitiativeLevel.LOW,
            evidence_bound=True,
            first_person_compliant=True,
            anti_decoration_compliant=True,
            stage_id=stage_id,
            recommended_action=None,
            handoff_triggered=False,
            prohibited_patterns_detected=[]
        )

    def _generate_situational_response(self, stage_id: str, tone: ToneEvaluation,
                                       evidence: Dict, situation: str,
                                       recommended_action: Optional[str]) -> str:
        """
        Generate the actual response text based on stage, tone, and evidence.
        Uses preset patterns as templates, fills with evidence.
        """
        preset = self.presets.get(tone.preset_name, self.presets.get("focused_warmth"))

        # Select pattern based on situation type
        if "progress" in situation.lower() or "crawl" in situation.lower() or "scan" in situation.lower():
            patterns = preset.get("progress_patterns", preset.get("opening_patterns", []))
        elif "complete" in situation.lower() or "done" in situation.lower() or "finished" in situation.lower():
            patterns = preset.get("closing_patterns", preset.get("opening_patterns", []))
        else:
            patterns = preset.get("opening_patterns", ["I'm ready to help."])

        if not patterns:
            patterns = ["I'm here to guide you through the next step."]

        # Pick first pattern (deterministic — no randomness in SKG)
        template = patterns[0]

        # Fill evidence variables
        text = self._fill_evidence(template, evidence)

        # If we have a recommended action, append guidance
        if recommended_action and tone.initiative != InitiativeLevel.LOW:
            text += f" The next step is {recommended_action.replace('_', ' ')}."

        return text

    def _generate_guidance_for_action(self, action: str, stage_id: str,
                                      tone: ToneEvaluation, evidence: Dict) -> str:
        """Generate guidance text for a specific approved action."""
        action_readable = action.replace("_", " ")

        if tone.humor_level == HumorLevel.FULL:
            return (
                f"I know exactly where you're headed. {action_readable.capitalize()} "
                f"is the right move from here — let me get that started for you. "
                f"The action is {action}."
            )
        elif tone.humor_level == HumorLevel.FOCUSED:
            return (
                f"That makes sense. The next approved step is {action_readable} ({action}). "
                f"Here's what happens when we do that."
            )
        else:
            return f"The next step is {action_readable} ({action}). Please confirm when ready."

    def _fill_evidence(self, template: str, evidence: Dict) -> str:
        """Replace {key} placeholders with evidence values."""
        text = template
        for key, value in evidence.items():
            placeholder = "{" + key + "}"
            if placeholder in text:
                text = text.replace(placeholder, str(value))
        return text

    def _contains_first_person(self, text: str) -> bool:
        """Return True when the text already uses first-person language."""
        lowered = text.lower()
        return bool(re.search(r"\bi\b|i'm|i'll|i've|i want|i know", lowered))

    def _enforce_first_person(self, text: str) -> tuple:
        """
        Ensure first-person usage. Detect and flag third-person references.
        Returns (corrected_text, is_compliant).
        """
        forbidden = [
            (r"\bthe system will\b", "I will"),
            (r"\bthe report indicates\b", "I found"),
            (r"\busers may proceed\b", "you can"),
            (r"\bthe orb will\b", "I will"),
            (r"\bit will\b", "I will"),
            (r"\bthis will\b", "I will"),
        ]

        compliant = True
        corrected = text
        had_issue = False

        for pattern, replacement in forbidden:
            if re.search(pattern, corrected, flags=re.IGNORECASE):
                had_issue = True
                corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)

        if not self._contains_first_person(corrected):
            corrected = "I want to help with this. " + corrected
            had_issue = True

        compliant = not had_issue
        return corrected, compliant

    def _detect_prohibited_patterns(self, text: str, tone: ToneEvaluation) -> List[str]:
        """Detect any prohibited patterns based on current tone level."""
        preset = self.presets.get(tone.preset_name, {})
        prohibited = preset.get("prohibited_patterns", [])
        detected = []

        text_lower = text.lower()
        for pattern in prohibited:
            pattern_lower = pattern.lower()
            if pattern_lower in text_lower:
                detected.append(pattern)
            elif pattern_lower == "generic motivational quotes" and any(marker in text_lower for marker in ["believe you can", "halfway there", "never give up", "you can do it", "just do it"]):
                detected.append(pattern)
            elif pattern_lower == "jokes at visitor expense" and any(marker in text_lower for marker in ["your website is", "your site is", "you should be embarrassed", "disaster"]):
                detected.append(pattern)

        if tone.humor_level == HumorLevel.QUIET and any(marker in text_lower for marker in ["joke", "funny", "worse", "laugh", "smile", "pun", "quip"]):
            detected.append("Humor in quiet stage")

        if any(marker in text_lower for marker in ["like a", "corn maze", "disaster", "embarrassed", "halfway there", "you can do it", "never give up"]):
            detected.append("Humorous or demeaning phrasing")

        if "disaster" in text_lower or "embarrassed" in text_lower:
            detected.append("disaster")

        # Global prohibitions from cognitive state
        global_prohibited = [
            "your site is terrible", "your website is bad", "you should be embarrassed",
            "even a child could", "this is a disaster", "what were you thinking"
        ]
        for pattern in global_prohibited:
            if pattern in text_lower:
                detected.append(f"GLOBAL_PROHIBITED: {pattern}")

        return detected

    def _check_evidence_bound(self, text: str, evidence: Dict, tone: ToneEvaluation) -> bool:
        """
        Check if humor in text is bound to actual evidence.
        If humor level is full or celebratory and a joke is present,
        it must reference a specific evidence key.
        """
        if tone.humor_level not in (HumorLevel.FULL, HumorLevel.CELEBRATORY):
            return True  # Non-humorous stages don't need evidence binding

        if not evidence:
            return False  # Humor requires evidence but none provided

        # Check if any evidence key appears in the text
        evidence_keys = [str(v).lower() for v in evidence.values() if isinstance(v, (str, int, float))]
        text_lower = text.lower()

        for key_val in evidence_keys:
            if key_val in text_lower:
                return True

        # If no evidence reference found, check for numbers that could be evidence
        import re
        numbers_in_text = re.findall(r'\d+', text)
        evidence_numbers = [str(v) for v in evidence.values() if isinstance(v, (int, float))]

        for num in numbers_in_text:
            if num in evidence_numbers:
                return True

        return False

    # ── State Management ───────────────────────────────────────

    def mark_screen_stable(self, stage_id: str):
        """Call this when the UI reports a screen as stable."""
        self.last_screen_stable_at = time.time()
        self.current_stage_id = stage_id
        self.control_handed_off = False

    def mark_visitor_input_start(self):
        """Call this when visitor begins typing or speaking."""
        self.visitor_input_active = True

    def mark_visitor_input_end(self):
        """Call this when visitor finishes input."""
        self.visitor_input_active = False

    def mark_handoff(self):
        """Call this when Weaver explicitly hands control to visitor."""
        self.control_handed_off = True


# ── Module-level convenience functions ─────────────────────────

_instance: Optional[WeaverArticulation] = None


def _get_instance() -> WeaverArticulation:
    global _instance
    if _instance is None:
        _instance = WeaverArticulation()
    return _instance


def articulate(context: Dict[str, Any]) -> WeaverResponse:
    """Entry point: articulate(context) → WeaverResponse"""
    return _get_instance().articulate(context)


def evaluate_tone(stage_id: str, evidence: Dict[str, Any] = None) -> ToneEvaluation:
    """Entry point: evaluate_tone(stage_id, evidence) → ToneEvaluation"""
    return _get_instance().evaluate_tone(stage_id, evidence or {})


def generate_response(envelope: Dict[str, Any]) -> str:
    """Entry point: generate_response(envelope) → str"""
    return _get_instance().generate_response(envelope)
