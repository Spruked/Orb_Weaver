import fs from 'fs';
import path from 'path';
import type { DiscoveryPattern } from '../../types/discovery';
import { DISCOVERY_DIMENSIONS } from '../../types/discovery';
import { DISCOVERY_PATTERNS, discoveryPatternById, LEGACY_PATTERN_RECONCILIATION, validateRegistry } from './registry';
import { LEGACY_ENGAGEMENT_QUESTIONS } from './legacyQuestions';
import { fallbackQuestion, renderQuestion } from './compiler';
import { LANDING_TOUR_CHAPTERS } from '../curriculum';

declare const test: (name: string, run: () => void | Promise<void>) => void;
declare const expect: any;

const lexicon = { slots: { host: { text: 'the website guide', evidenceId: 'site:host' } } };

test('all 50 records preserve the owner source meaning, order, and fallback text', () => {
  const canonical = fs.readFileSync(path.resolve(process.cwd(), '../docs/architecture/NINE_OF_CLUBS_CANONICAL_SOURCE.md'), 'utf8');
  const questions = [...canonical.matchAll(/(\d+)\.\s+\*\*(.+?)\*\*\s+`([^`]+)`/gs)];
  expect(questions).toHaveLength(50);
  expect(DISCOVERY_PATTERNS).toHaveLength(50);
  for (const [, number, prompt, semantics] of questions) {
    const pattern = discoveryPatternById(`NOC_${number.padStart(2, '0')}`)!;
    expect(pattern).not.toBeNull();
    expect(pattern.choices.map(choice => choice.semanticOutput)).toEqual(semantics.split(' / '));
    const neutralPrompt = prompt.replace(/\bthe ORB\b/g, '{host}').replace(/\ban ORB\b/g, '{host}').replace(/\bORB\b/g, '{host}');
    expect(pattern.fallbackRendering).toBe(neutralPrompt);
    expect(renderQuestion(pattern, lexicon, fallbackQuestion(pattern, lexicon)))
      .toBe(neutralPrompt.replace(/\{host\}/g, 'the website guide'));
    for (const choice of pattern.choices) {
      expect(choice.candidateAction.topic).toBe(choice.semanticOutput);
      expect(choice.candidateAction.id).toBe(`${choice.candidateAction.kind}:${choice.semanticOutput}`);
    }
  }
  expect(new Set(DISCOVERY_PATTERNS.map(pattern => pattern.dimension)))
    .toEqual(new Set(DISCOVERY_DIMENSIONS));
});

test('registry is immutable and corrupted authority data fails validation', () => {
  expect(Object.isFrozen(DISCOVERY_PATTERNS)).toBe(true);
  expect(Object.isFrozen(DISCOVERY_PATTERNS[0].choices[0].candidateAction)).toBe(true);
  for (const mutate of [
    (p: DiscoveryPattern[]) => { p[1].id = p[0].id; },
    (p: DiscoveryPattern[]) => { p[0].choices.pop(); },
    (p: DiscoveryPattern[]) => { p[0].choices[1].semanticOutput = p[0].choices[0].semanticOutput; },
    (p: DiscoveryPattern[]) => { p[0].choices[0].candidateAction.topic = 'UNDECLARED'; },
    (p: DiscoveryPattern[]) => { p[49].choices[0].candidateAction.requiresExplicitConsent = false; },
    (p: DiscoveryPattern[]) => { p[0].generationConstraints.allowYesNoExit = true; },
    (p: DiscoveryPattern[]) => { p[0].confidenceTarget = Number.NaN; },
  ]) {
    const records: DiscoveryPattern[] = JSON.parse(JSON.stringify(DISCOVERY_PATTERNS));
    mutate(records);
    expect(() => validateRegistry(records)).toThrow();
  }
});

test('three distinct legacy topologies are shared with the curriculum, not relabeled as triads', () => {
  const authored = LANDING_TOUR_CHAPTERS.flatMap(chapter => chapter.stops.flatMap(stop => stop.engagementQuestion ? [stop.engagementQuestion] : []));
  expect(authored).toHaveLength(3);
  for (const question of authored) {
    expect(question).toBe(LEGACY_ENGAGEMENT_QUESTIONS[question.id]);
    expect(question.options).toHaveLength(2);
    const reconciliation = LEGACY_PATTERN_RECONCILIATION[question.id as keyof typeof LEGACY_PATTERN_RECONCILIATION];
    expect(reconciliation.disposition).toBe('retain_distinct_two_choice_topology');
    expect(reconciliation.relatedPatternIds.every(id => discoveryPatternById(id))).toBe(true);
  }
});
