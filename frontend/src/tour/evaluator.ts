import type { ChapterEvaluation, TourConcept } from '../types/tour';

// Conservative, deterministic content checks. A claimed ID and a copied generic
// sentence are insufficient. Unrecognized or ambiguous coverage stays pending.
const evidenceRules: Record<string, RegExp[]> = {
  WEAVER_IDENTITY: [/weaver/i, /website|site/i, /host|guid|explain|knowledge/i],
  PRESENCE_AND_CONTROL: [/speak|talk/i, /natural/i, /click|interrupt|stop|pause/i, /control/i],
  VERIFIED_GUIDANCE: [/verif/i, /target|point/i, /live/i, /ping/i],
  CRAWL_VS_WEAVE: [/a crawl discovers pages/i, /a weave discovers purpose/i],
  RELATIONSHIP_MODEL: [/relationship|connect/i, /product/i, /service/i, /polic/i, /journey/i],
  WEBSITE_ORB_OUTCOME: [/website orb/i, /greet/i, /guid/i, /underst/i, /help/i, /finish/i],
  TRUST_SECURITY_GOVERNANCE: [/secur/i, /govern/i, /verif/i, /permission/i],
  TWENTY_EIGHT_WEAVE: [/28|twenty.eight/i, /manufactur|process/i, /knowledge/i, /pointer/i, /learn/i],
  UNIQUE_WEAVES: [/a priori/i, /a posteriori/i, /multi.funnel continuity/i, /pointer intelligence/i],
  BUSINESS_OUTCOMES: [/confusion/i, /journey/i, /abandon/i, /engagement/i, /trust/i, /decision/i],
  PREFLIGHT_PURPOSE: [/preflight/i, /free/i, /readiness|first weave/i, /scan/i],
  PREFLIGHT_CHOICE: [/preflight/i, /choose|choice|decid/i, /explor|onboarding/i],
};

export function verifiedConceptIds(evaluation: ChapterEvaluation, required: TourConcept[]): string[] {
  const allowed = new Set(required.map(concept => concept.id));
  const verified = new Set<string>();
  for (const claim of evaluation.covered_concepts) {
    const excerpt = claim.supporting_excerpt.trim();
    const rules = evidenceRules[claim.concept_id];
    if (!allowed.has(claim.concept_id) || !rules || excerpt.length < 24) continue;
    if (!evaluation.spoken_output.includes(excerpt)) continue;
    if (rules.every(rule => rule.test(excerpt))) verified.add(claim.concept_id);
  }
  return [...verified];
}

export function parseChapterEvaluation(value: unknown, spokenOutput: string): ChapterEvaluation {
  const candidate = value as Partial<ChapterEvaluation> | null;
  if (!candidate || candidate.spoken_output !== spokenOutput || !Array.isArray(candidate.covered_concepts)) {
    throw new Error('Weaver’s response did not include usable concept evidence. Your tour position is saved.');
  }
  return {
    spoken_output: spokenOutput,
    covered_concepts: candidate.covered_concepts.filter(claim =>
      claim && typeof claim.concept_id === 'string' && typeof claim.supporting_excerpt === 'string'),
    detected_visitor_intent: typeof candidate.detected_visitor_intent === 'string' ? candidate.detected_visitor_intent : null,
    suggested_transition: typeof candidate.suggested_transition === 'string' ? candidate.suggested_transition : null,
  };
}
