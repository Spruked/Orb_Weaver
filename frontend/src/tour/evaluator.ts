import type { ChapterEvaluation, TourConcept } from '../types/tour';

export function verifiedConceptIds(evaluation: ChapterEvaluation, required: TourConcept[]): string[] {
  const allowed = new Map(required.map(concept => [concept.id, concept]));
  const verified = new Set<string>();
  for (const claim of evaluation.covered_concepts) {
    const excerpt = claim.supporting_excerpt.trim();
    const concept = allowed.get(claim.concept_id);
    if (!concept || !excerpt) continue;
    if (!evaluation.spoken_output.includes(excerpt)) continue;
    const normalizedExcerpt = excerpt.toLocaleLowerCase();
    if (!(concept.coverageRequirements || []).every(requirement => normalizedExcerpt.includes(requirement.toLocaleLowerCase()))) continue;
    verified.add(claim.concept_id);
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
