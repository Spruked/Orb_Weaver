"""
Wrapper that constrains an LLM's movement decision to the ontology's
closed vocabulary and rejects anything that doesn't resolve cleanly —
before it ever reaches the HAL.
"""
from owlready2 import get_ontology

onto = get_ontology("movement_skg.owl").load()

VALID_INTENTS = {cls.name for cls in onto.MovementIntent.descendants()} - {"MovementIntent"}

def get_pois_for_route(route: str):
    return [ind for ind in onto.PointOfInterest.instances() if ind.onRoute == [route]]

def serialize_context_for_llm(pois, voice_state: str, transcript: str) -> str:
    lines = [f"route pois: {[p.hasTargetId[0] for p in pois]}",
             f"voice_state: {voice_state}", f"transcript: {transcript}",
             f"allowed_intents: {sorted(VALID_INTENTS)}"]
    return "\n".join(lines)

def validate_decision(decision: dict, pois) -> tuple[bool, str]:
    if decision.get("intent") not in VALID_INTENTS:
        return False, "intent_not_in_ontology"
    target_id = decision.get("targetId")
    if target_id and not any(p.hasTargetId[0] == target_id for p in pois):
        return False, "target_not_found_on_route"
    return True, "ok"

def decide_movement(route: str, voice_state: str, transcript: str, llm_call) -> dict | None:
    pois = get_pois_for_route(route)
    context = serialize_context_for_llm(pois, voice_state, transcript)
    decision = llm_call(context)  # must return dict with intent/targetId/urgency/etc.
    ok, reason = validate_decision(decision, pois)
    if not ok:
        # fall back to idle presence rather than trust an out-of-vocabulary decision
        return None
    return decision
