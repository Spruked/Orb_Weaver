"""
Context & Correspondence Orchestrator - Task Analyzer
Extracts intent, entities, and information priorities from task descriptions
to guide compression strategy.
"""

import re
from typing import List, Dict, Any
from ..models import TaskProfile


class TaskAnalyzer:
    """Analyzes task descriptions to guide context compression."""

    DOMAIN_PATTERNS = {
        "warranty": ["warranty", "guarantee", "repair", "defect", "coverage", "claim"],
        "legal": ["contract", "agreement", "liability", "compliance", "regulation", "law"],
        "technical": ["code", "api", "function", "architecture", "implementation", "debug"],
        "medical": ["diagnosis", "treatment", "symptom", "patient", "prescription", "clinical"],
        "financial": ["revenue", "expense", "budget", "investment", "audit", "accounting"],
        "support": ["ticket", "issue", "troubleshoot", "customer", "help", "faq"],
        "sales": ["pricing", "discount", "quote", "proposal", "lead", "prospect"],
    }

    NEED_PATTERNS = {
        "factual": ["what is", "what are", "list", "enumerate", "identify"],
        "procedural": ["how to", "steps", "process", "procedure", "guide", "tutorial"],
        "comparative": ["compare", "difference", "versus", "vs", "better", "worse"],
        "diagnostic": ["why", "cause", "reason", "explain", "diagnose", "analyze"],
        "temporal": ["when", "timeline", "history", "schedule", "deadline", "date"],
        "locative": ["where", "location", "address", "place", "site"],
    }

    def __init__(self):
        self.temporal_regex = [
            re.compile(r'\b(19|20)\d{2}\b'),
            re.compile(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\b', re.I),
            re.compile(r'\bQ[1-4]\s+(19|20)\d{2}\b', re.I),
            re.compile(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b'),
            re.compile(r'\b(current|recent|latest|upcoming|past|previous|next|last|first)\b', re.I),
        ]

    def analyze(self, task: str) -> TaskProfile:
        """Extract task profile from description."""
        task_lower = task.lower()

        domain = self._detect_domain(task_lower)
        entities = self._extract_entities(task)
        information_needs = self._detect_needs(task_lower)
        priority_keywords = self._extract_priority_keywords(task_lower)
        temporal_constraints = self._detect_temporal(task)
        intent = self._determine_intent(task_lower, information_needs)

        return TaskProfile(
            intent=intent,
            entities=entities,
            information_needs=information_needs,
            priority_keywords=priority_keywords,
            temporal_constraints=temporal_constraints,
            domain=domain
        )

    def _detect_domain(self, task: str) -> str:
        scores = {domain: sum(1 for kw in keywords if kw in task) 
                  for domain, keywords in self.DOMAIN_PATTERNS.items()}
        valid_scores = {k: v for k, v in scores.items() if v > 0}
        return max(valid_scores, key=valid_scores.get) if valid_scores else "general"

    def _extract_entities(self, task: str) -> List[str]:
        entities = []
        entities.extend(re.findall(r'"([^"]+)"', task))
        entities.extend(re.findall(r"'([^']+)'", task))
        entities.extend(re.findall(r'\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*){1,3}\b', task))
        entities.extend(re.findall(r'\b[A-Z]{2,}-?\d+[A-Z\-\d]*\b', task))
        return list(set(e for e in entities if len(e) > 1))[:20]

    def _detect_needs(self, task: str) -> List[str]:
        needs = [need for need, patterns in self.NEED_PATTERNS.items() 
                 if any(p in task for p in patterns)]
        return needs if needs else ["factual"]

    def _extract_priority_keywords(self, task: str) -> List[str]:
        keywords = []
        # Focus phrases
        for match in re.finditer(r'(?:focus|concentrate|emphasis|priority|important|key|critical|essential|main|primary|core|specifically|particularly|especially|relevant|related|regarding|about|concerning|pertaining to|involving|dealing with|addressing|covering|discussing|explaining|describing|detailing|identifying|determining|establishing|confirming|verifying|analyzing|evaluating|assessing|measuring|calculating|estimating|predicting|forecasting|planning|strategizing|organizing|structuring|arranging|ordering|sequencing|prioritizing|ranking|comparing|contrasting|differentiating|categorizing|classifying|grouping|clustering|segmenting|partitioning|dividing|separating|isolating|extracting|retrieving|recovering|restoring|reconstructing|rebuilding|recreating|reproducing|replicating|copying|duplicating|summarizing|condensing|compressing|reducing|shrinking|minimizing|maximizing|optimizing|enhancing|improving|upgrading|updating|modernizing|refining|perfecting|completing|finishing|concluding|closing|ending|terminating|stopping|halting|pausing|suspending|delaying|postponing|deferring|rescheduling|replanning|reorganizing|restructuring|reforming|transforming|converting|changing|altering|modifying|adjusting|adapting|customizing|personalizing|tailoring|fitting|suiting|matching|aligning|harmonizing|balancing|equalizing|standardizing|normalizing|regularizing|systematizing|methodizing|routinizing|automating|mechanizing|computerizing|digitizing|virtualizing|simulating|modeling|representing|depicting|portraying|illustrating|demonstrating|showing|displaying|exhibiting|presenting|revealing|disclosing|exposing|uncovering|discovering|finding|locating|pinpointing|identifying|recognizing|acknowledging|accepting|adopting|embracing|welcoming|receiving|obtaining|acquiring|gaining|earning|winning|achieving|accomplishing|attaining|reaching|arriving|accessing|entering|joining|participating|engaging|interacting|communicating|corresponding|connecting|linking|relating|associating|affiliating|allying|partnering|collaborating|cooperating|coordinating|synchronizing|integrating|unifying|consolidating|merging|combining|blending|mixing|fusing|welding|bonding|fastening|securing|anchoring|grounding|rooting|basing|founding|establishing|creating|making|building|constructing|assembling|fabricating|manufacturing|producing|generating|forming|shaping|molding|casting|forging|crafting|designing|engineering|inventing|innovating|developing|evolving|growing|expanding|extending|stretching|spreading|distributing|dispersing|scattering|sprinkling|spraying|pouring|dumping|throwing|tossing|flipping|turning|rotating|spinning|twirling|swirling|whirling|circling|orbiting|revolving|pivoting|swiveling|hinging|depending|relying|trusting|believing|thinking|knowing|understanding|comprehending|grasping|seizing|capturing|catching|grabbing|snatching|plucking|picking|selecting|choosing|electing|voting|deciding|determining|resolving|settling|fixing|repairing|mending|healing|curing|treating|handling|managing|directing|leading|guiding|steering|piloting|navigating|sailing|cruising|driving|riding|flying|soaring|gliding|floating|drifting|sinking|diving|plunging|jumping|leaping|hopping|skipping|bounding|springing|bouncing|ricocheting|rebounding|recoiling|resiling|recovering|retrieving|reclaiming|redeeming|ransoming|rescuing|saving|preserving|protecting|guarding|defending|shielding|screening|sheltering|housing|accommodating|lodging|quartering|billeting|stationing|posting|positioning|placing|locating|situating)\s+(?:on|about|regarding|concerning|pertaining to|related to|relevant to|involving|dealing with|addressing|covering|discussing|explaining|describing|detailing|identifying|determining|establishing|confirming|verifying|analyzing|evaluating|assessing|measuring|calculating|estimating|predicting|forecasting|planning|strategizing|organizing|structuring|arranging|ordering|sequencing|prioritizing|ranking|comparing|contrasting|differentiating|categorizing|classifying|grouping|clustering|segmenting|partitioning|dividing|separating|isolating|extracting|retrieving|recovering|restoring|reconstructing|rebuilding|recreating|reproducing|replicating|copying|duplicating|summarizing|condensing|compressing|reducing|shrinking|minimizing|maximizing|optimizing|enhancing|improving|upgrading|updating|modernizing|refining|perfecting|completing|finishing|concluding|closing|ending|terminating|stopping|halting|pausing|suspending|delaying|postponing|deferring|rescheduling|replanning|reorganizing|restructuring|reforming|transforming|converting|changing|altering|modifying|adjusting|adapting|customizing|personalizing|tailoring|fitting|suiting|matching|aligning|harmonizing|balancing|equalizing|standardizing|normalizing|regularizing|systematizing|methodizing|routinizing|automating|mechanizing|computerizing|digitizing|virtualizing|simulating|modeling|representing|depicting|portraying|illustrating|demonstrating|showing|displaying|exhibiting|presenting|revealing|disclosing|exposing|uncovering|discovering|finding|locating|pinpointing|identifying|recognizing|acknowledging|accepting|adopting|embracing|welcoming|receiving|obtaining|acquiring|gaining|earning|winning|achieving|accomplishing|attaining|reaching|arriving|accessing|entering|joining|participating|engaging|interacting|communicating|corresponding|connecting|linking|relating|associating|affiliating|allying|partnering|collaborating|cooperating|coordinating|synchronizing|integrating|unifying|consolidating|merging|combining|blending|mixing|fusing|welding|bonding|fastening|securing|anchoring|grounding|rooting|basing|founding|establishing|creating|making|building|constructing|assembling|fabricating|manufacturing|producing|generating|forming|shaping|molding|casting|forging|crafting|designing|engineering|inventing|innovating|developing|evolving|growing|expanding|extending|stretching|spreading|distributing|dispersing|scattering|sprinkling|spraying|pouring|dumping|throwing|tossing|flipping|turning|rotating|spinning|twirling|swirling|whirling|circling|orbiting|revolving|pivoting|swiveling|hinging|depending|relying|trusting|believing|thinking|knowing|understanding|comprehending|grasping|seizing|capturing|catching|grabbing|snatching|plucking|picking|selecting|choosing|electing|voting|deciding|determining|resolving|settling|fixing|repairing|mending|healing|curing|treating|handling|managing|directing|leading|guiding|steering|piloting|navigating|sailing|cruising|driving|riding|flying|soaring|gliding|floating|drifting|sinking|diving|plunging|jumping|leaping|hopping|skipping|bounding|springing|bouncing|ricocheting|rebounding|recoiling|resiling|recovering|retrieving|reclaiming|redeeming|ransoming|rescuing|saving|preserving|protecting|guarding|defending|shielding|screening|sheltering|housing|accommodating|lodging|quartering|billeting|stationing|posting|positioning|placing|locating|situating)\s+([\w\s]+?)(?:\.|,|;|and\b|or\b|but\b|however\b)', task):
            group = match.group(1).strip()
            if len(group) > 2:
                keywords.append(group)

        # Extract nouns after articles
        for match in re.finditer(r'\b(the|a|an)\s+([\w\s]{3,40}?)(?:\s+(?:is|are|was|were|has|have|had|can|could|will|would|shall|should|may|might|must)\b|\.|,|;)', task, re.I):
            group = match.group(2).strip()
            if len(group) > 2:
                keywords.append(group)

        return list(set(kw.lower() for kw in keywords if len(kw) > 2))[:20]

    def _detect_temporal(self, task: str) -> List[str]:
        constraints = []
        for regex in self.temporal_regex:
            matches = regex.findall(task)
            constraints.extend(matches if isinstance(matches, list) else [matches])
        return list(set(str(c) for c in constraints if c))

    def _determine_intent(self, task: str, needs: List[str]) -> str:
        if "how to" in task or "procedural" in needs:
            return "procedural"
        elif any(n in ["comparative", "diagnostic"] for n in needs):
            return "analytical"
        elif "factual" in needs:
            return "informational"
        else:
            return "general"

    def score_chunk_relevance(self, task_profile: TaskProfile, chunk_text: str) -> float:
        """Score how relevant a text chunk is to a task profile."""
        chunk_lower = chunk_text.lower()
        score = 0.0

        if task_profile.domain and task_profile.domain != "general":
            domain_kws = self.DOMAIN_PATTERNS.get(task_profile.domain, [])
            score += sum(0.3 for kw in domain_kws if kw in chunk_lower)

        for kw in task_profile.priority_keywords:
            if kw.lower() in chunk_lower:
                score += 0.5

        for entity in task_profile.entities:
            if entity.lower() in chunk_lower:
                score += 0.4

        for need in task_profile.information_needs:
            if need == "procedural" and any(w in chunk_lower for w in ["step", "how", "process", "procedure"]):
                score += 0.3
            elif need == "temporal" and any(w in chunk_lower for w in ["date", "time", "when", "schedule", "202", "19"]):
                score += 0.3
            elif need == "comparative" and any(w in chunk_lower for w in ["vs", "versus", "compare", "difference", "than"]):
                score += 0.3

        return min(score, 5.0)
