import source from './patterns.json';
import { DISCOVERY_DIMENSIONS } from '../../types/discovery';
import type { DiscoveryPattern } from '../../types/discovery';

export function freezeRegistry<T>(value: T): T {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freezeRegistry);
    Object.freeze(value);
  }
  return value;
}

const stages = ['LANDING_TOUR', 'PREFLIGHT', 'ONBOARDING', 'PRODUCTION_SCAN'];
const kinds = ['EXPLAIN', 'DEMONSTRATE', 'REVIEW_COMMERCIAL_FIT', 'REQUEST_SITE_SCAN', 'REQUEST_CONFIGURATION', 'REVIEW_IMPLEMENTATION'];
const unit = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n) && n >= 0 && n <= 1;
const text = (s: unknown): s is string => typeof s === 'string' && s.trim().length > 0;

/** Validate shipped authority data once, before it is made available to cognition. */
export function validateRegistry(patterns: readonly DiscoveryPattern[]): void {
  const ids = new Set<string>();
  const numbers = new Set<number>();
  for (const pattern of patterns) {
    if (ids.has(pattern.id) || numbers.has(pattern.sourceNumber) ||
      !Number.isInteger(pattern.sourceNumber) || pattern.sourceNumber < 1 || pattern.sourceNumber > 50 ||
      pattern.id !== `NOC_${String(pattern.sourceNumber).padStart(2, '0')}`) throw new Error('Invalid or duplicate pattern identity');
    ids.add(pattern.id);
    numbers.add(pattern.sourceNumber);
    if (!DISCOVERY_DIMENSIONS.includes(pattern.dimension) || !text(pattern.intent) ||
      !unit(pattern.confidenceTarget) || !unit(pattern.informationGainWeight) || !unit(pattern.convergenceWeight)) {
      throw new Error(`Invalid dimension or ranking policy: ${pattern.id}`);
    }
    if (!pattern.legalStages.length || pattern.legalStages.some(stage => !stages.includes(stage)) ||
      pattern.requiredDimensions.some(dimension => !DISCOVERY_DIMENSIONS.includes(dimension))) throw new Error('Invalid stage policy');
    const constraints = pattern.generationConstraints;
    if (pattern.choices.length !== 3 || constraints.choiceCount !== 3 || !constraints.preserveOrder ||
      constraints.allowAdditionalBranches || constraints.allowYesNoExit) throw new Error('Invalid canonical topology');
    const codes = pattern.choices.map(choice => choice.semanticOutput);
    if (new Set(codes).size !== 3 || codes.some(code => !/^[A-Z][A-Z0-9_]*$/.test(code))) throw new Error('Invalid semantic outputs');
    for (const choice of pattern.choices) {
      const action = choice.candidateAction;
      if (!text(choice.fallbackLabel) || !kinds.includes(action.kind) || action.topic !== choice.semanticOutput ||
        action.id !== `${action.kind}:${action.topic}` || typeof action.requiresExplicitConsent !== 'boolean' ||
        typeof action.requiresLiveVerification !== 'boolean') throw new Error('Missing or invalid candidate action');
      if ((action.kind === 'REQUEST_SITE_SCAN' || action.kind === 'REQUEST_CONFIGURATION') && !action.requiresExplicitConsent) {
        throw new Error('Operational action must require explicit consent');
      }
      if (action.kind === 'DEMONSTRATE' && !action.requiresLiveVerification) throw new Error('Demonstration requires live proof');
    }
    const [a, b, c] = pattern.choices.map(choice => choice.fallbackLabel);
    if (pattern.fallbackRendering !== `${pattern.fallbackStem} — ${a}, ${b}, or ${c}?`) throw new Error('Fallback topology mismatch');
    const slots = Array.from(pattern.fallbackRendering.matchAll(/\{([a-z_]+)\}/g), match => match[1]);
    if (new Set(pattern.requiredLexicalSlots).size !== pattern.requiredLexicalSlots.length ||
      slots.some(slot => !pattern.requiredLexicalSlots.includes(slot)) ||
      pattern.requiredLexicalSlots.some(slot => !slots.includes(slot))) throw new Error('Lexical slot mismatch');
  }
  if (patterns.length !== 50) throw new Error('The canonical bank must contain exactly 50 patterns');
}

if (source.schemaVersion !== 1) throw new Error('Unsupported discovery registry version');
validateRegistry(source.patterns as DiscoveryPattern[]);
export const DISCOVERY_PATTERNS: readonly DiscoveryPattern[] = freezeRegistry(source.patterns as DiscoveryPattern[]);

export function discoveryPatternById(id: string): DiscoveryPattern | null {
  return DISCOVERY_PATTERNS.find(pattern => pattern.id === id) || null;
}

/** Similar purposes, but different topology: these are links, not semantic aliases. */
export const LEGACY_PATTERN_RECONCILIATION = freezeRegistry({
  'discovery-or-guidance': { relatedPatternIds: ['NOC_01', 'NOC_31'], disposition: 'retain_distinct_two_choice_topology' },
  'understanding-or-helping': { relatedPatternIds: ['NOC_11', 'NOC_41'], disposition: 'retain_distinct_two_choice_topology' },
  'discovery-or-conversion': { relatedPatternIds: ['NOC_02'], disposition: 'retain_distinct_two_choice_topology' },
});
