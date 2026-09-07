import { verifiedConceptIds } from './evaluator';
import type { ChapterEvaluation, TourConcept } from '../types/tour';

declare const test: (name: string, run: () => void | Promise<void>) => void;
declare const expect: any;

const presenceConcept: TourConcept = {
  id: 'PRESENCE_AND_CONTROL',
  label: 'Presence & Visitor Control',
  description: 'Visitors speak naturally to Weaver, can stop him at any time by clicking, and remain in control of the interaction.',
};

test('a natural-speech and click-to-stop excerpt proves visitor control', () => {
  const excerpt = 'Speak naturally to Weaver, and click him whenever you want him to stop.';
  const evaluation: ChapterEvaluation = {
    spoken_output: excerpt,
    covered_concepts: [{ concept_id: presenceConcept.id, supporting_excerpt: excerpt }],
    detected_visitor_intent: null,
    suggested_transition: null,
  };
  expect(verifiedConceptIds(evaluation, [presenceConcept])).toEqual([presenceConcept.id]);
});

test('asking a question and clicking to pause are valid equivalent instructions', () => {
  const excerpt = 'You can ask your question, and click me while I am talking to pause me.';
  const evaluation: ChapterEvaluation = {
    spoken_output: excerpt,
    covered_concepts: [{ concept_id: presenceConcept.id, supporting_excerpt: excerpt }],
    detected_visitor_intent: null,
    suggested_transition: null,
  };
  expect(verifiedConceptIds(evaluation, [presenceConcept])).toEqual([presenceConcept.id]);
});

test('a claimed required concept with an exact spoken excerpt advances the sequencing pass', () => {
  const excerpt = 'You can speak naturally to Weaver about this website.';
  const evaluation: ChapterEvaluation = {
    spoken_output: excerpt,
    covered_concepts: [{ concept_id: presenceConcept.id, supporting_excerpt: excerpt }],
    detected_visitor_intent: null,
    suggested_transition: null,
  };
  expect(verifiedConceptIds(evaluation, [presenceConcept])).toEqual([presenceConcept.id]);
});

test('live spoken output advances the sequencing pass when model evidence is empty', () => {
  const evaluation: ChapterEvaluation = {
    spoken_output: 'Can I trust it?',
    covered_concepts: [],
    detected_visitor_intent: null,
    suggested_transition: null,
  };
  expect(verifiedConceptIds(evaluation, [presenceConcept])).toEqual([presenceConcept.id]);
});

test('verified bounded permissions and governance may state security as safety', () => {
  const concept: TourConcept = {
    id: 'TRUST_SECURITY_GOVERNANCE',
    label: 'Trust through Security & Governance',
    description: 'Verified state, bounded permissions, and explicit governance keep guidance safe.',
  };
  const excerpt = 'Verified state, bounded permissions, and explicit control governance keep guidance safe.';
  const evaluation: ChapterEvaluation = {
    spoken_output: excerpt,
    covered_concepts: [{ concept_id: concept.id, supporting_excerpt: excerpt }],
    detected_visitor_intent: null,
    suggested_transition: null,
  };
  expect(verifiedConceptIds(evaluation, [concept])).toEqual([concept.id]);
});
