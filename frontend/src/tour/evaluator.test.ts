import { verifiedConceptIds } from './evaluator';
import type { ChapterEvaluation, TourConcept } from '../types/tour';

declare const test: (name: string, run: () => void | Promise<void>) => void;
declare const expect: any;

const presenceConcept: TourConcept = {
  id: 'PRESENCE_AND_CONTROL',
  label: 'Presence & Visitor Control',
  description: 'Visitors speak naturally and hands-free; Weaver listens after they pause and rearms for the next turn. They remain in control of the interaction.',
  coverageRequirements: ['hands-free', 'speak naturally', 'remain in control'],
};

test('hands-free natural speech proves visitor control', () => {
  const excerpt = 'Speak naturally, hands-free. You remain in control of the interaction.';
  const evaluation: ChapterEvaluation = {
    spoken_output: excerpt,
    covered_concepts: [{ concept_id: presenceConcept.id, supporting_excerpt: excerpt }],
    detected_visitor_intent: null,
    suggested_transition: null,
  };
  expect(verifiedConceptIds(evaluation, [presenceConcept])).toEqual([presenceConcept.id]);
});

test('click-only speech cannot prove the hands-free conversation contract', () => {
  const excerpt = 'Click me while I am talking to pause me.';
  const evaluation: ChapterEvaluation = {
    spoken_output: excerpt,
    covered_concepts: [{ concept_id: presenceConcept.id, supporting_excerpt: excerpt }],
    detected_visitor_intent: null,
    suggested_transition: null,
  };
  expect(verifiedConceptIds(evaluation, [presenceConcept])).toEqual([]);
});

test('partial natural-speech instruction cannot advance the sequencing pass', () => {
  const excerpt = 'You can speak naturally to Weaver about this website.';
  const evaluation: ChapterEvaluation = {
    spoken_output: excerpt,
    covered_concepts: [{ concept_id: presenceConcept.id, supporting_excerpt: excerpt }],
    detected_visitor_intent: null,
    suggested_transition: null,
  };
  expect(verifiedConceptIds(evaluation, [presenceConcept])).toEqual([]);
});

test('speech without verified concept evidence does not advance the sequencing pass', () => {
  const evaluation: ChapterEvaluation = {
    spoken_output: 'Can I trust it?',
    covered_concepts: [],
    detected_visitor_intent: null,
    suggested_transition: null,
  };
  expect(verifiedConceptIds(evaluation, [presenceConcept])).toEqual([]);
});

test('an identity introduction without all required meaning cannot advance', () => {
  const identity: TourConcept = {
    id: 'WEAVER_IDENTITY',
    description: 'Weaver is the Website ORB host who understands this website, answers from verified knowledge, and guides to the right place when showing is faster than explaining.',
    coverageRequirements: ['Website ORB host', 'this website', 'verified knowledge', 'right place', 'show', 'explain'],
  };
  const excerpt = 'I am Weaver, the Website ORB host. I understand this website and guide you to the right place.';
  const evaluation: ChapterEvaluation = {
    spoken_output: excerpt,
    covered_concepts: [{ concept_id: identity.id, supporting_excerpt: excerpt }],
    detected_visitor_intent: null,
    suggested_transition: null,
  };
  expect(verifiedConceptIds(evaluation, [identity])).toEqual([]);
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
