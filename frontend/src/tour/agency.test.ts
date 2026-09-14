import { createInitialJourneyState } from '../state/tourControllerStore';
import type { AgencyBinding, AgencyEnvironment } from '../types/agency';
import { createAgencyEnvelope, validAgencyBinding } from './governor';
import { AGENCY_BUDGET, boundedAgencyInput } from './agencyBudget';
import { DISCOVERY_PATTERNS } from './discovery/registry';
import { webcrypto } from 'crypto';

Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });

declare const test: (name: string, run: () => void | Promise<void>) => void;
declare const expect: any;

const explanation: AgencyBinding = {
  binding_id: 'explain', purpose: 'Explain current evidence', cognitive_action: 'EXPLAIN', choreography: 'EXPLAIN_IN_PLACE',
  permission_tier: 'OBSERVE', requires_confirmation: false, evidence_basis: ['page'], preconditions: ['active'],
};

function environment(bindings: AgencyBinding[] = [explanation]): AgencyEnvironment {
  const ids = bindings.map(binding => binding.binding_id);
  return {
    journey: createInitialJourneyState(), route: '/', positionRevision: 1, domRevision: 1, visitorRevision: 1, evidenceRevision: 1, permissionRevision: 1,
    universalCapabilities: [...ids], scannedAffordances: [...ids], liveAffordances: [...ids], governedCapabilities: [...ids], policyCapabilities: [...ids],
    permissionTiers: ['OBSERVE', 'NAVIGATE'], confirmations: [], validEvidenceIds: ['page', 'target'], satisfiedPreconditions: ['active'],
    legalStageTransitions: [], destinations: { DETAILS: { route: '/features', evidenceId: 'target', targetAlias: 'FEATURE_CONTROL' } },
    spatialTargets: { FEATURE_CONTROL: { targetId: 'feature-control', evidenceId: 'target' } }, bindings,
    acquisition: { confidenceByDimension: {}, askedPatternIds: [], remainingAcquisitions: 3,
      availableCandidateActionIds: DISCOVERY_PATTERNS.flatMap(pattern => pattern.choices.map(choice => choice.candidateAction.id)) },
  };
}

test('coherent candidates use only relevant vectors; explanation requires no question, route or target', async () => {
  const env = environment();
  const governor = createAgencyEnvelope(() => env);
  const envelope = governor.refresh();
  expect(envelope.candidates).toHaveLength(1);
  expect(envelope.vectors.LEGAL_PATTERNS).toEqual([]);
  expect(envelope.vectors.LEGAL_STAGE_TRANSITIONS).toEqual([]);
  expect(envelope.candidates[0]).not.toHaveProperty('semantic_target');
  expect(envelope.candidates[0]).not.toHaveProperty('pattern_id');
  const token = governor.issue({ selected_candidate_id: envelope.candidates[0].candidate_id }, envelope.bounded_set_revision)!;
  let spoken = 0;
  expect(await governor.execute(token, async move => { expect(move.cognitive_action).toBe('EXPLAIN'); spoken += 1; return true; })).toBe(true);
  expect(spoken).toBe(1);
  expect(await governor.execute(token, async () => { spoken += 1; return true; })).toBe(false);
  expect(spoken).toBe(1);
});

test('each of the six intersection inputs removes unavailable actions', () => {
  for (const key of ['universalCapabilities', 'scannedAffordances', 'liveAffordances', 'governedCapabilities', 'policyCapabilities', 'permissionTiers'] as const) {
    const env = environment();
    env[key] = [];
    expect(createAgencyEnvelope(() => env).refresh().candidates).toEqual([]);
  }
});

test('unknown candidate IDs and malformed or authority-injecting cognition fail closed', () => {
  const governor = createAgencyEnvelope(() => environment());
  const envelope = governor.refresh();
  const id = envelope.candidates[0].candidate_id;
  for (const selection of [null, [], 'explain', { selected_candidate_id: 'invented' },
    { selected_candidate_id: id, route: '/checkout' }, { selected_candidate_id: id, confidence: Number.NaN },
    { selected_candidate_id: id, confidence: 2 }, { selected_candidate_id: id, candidate: envelope.candidates[0] }]) {
    expect(governor.issue(selection, envelope.bounded_set_revision)).toBeNull();
  }
});

test('every relevant event invalidates an old model reply and unconsumed token', () => {
  for (const event of ['position', 'route', 'dom', 'target', 'permissions', 'visitor', 'evidence'] as const) {
    const env = environment();
    const governor = createAgencyEnvelope(() => env);
    const envelope = governor.refresh();
    const selection = { selected_candidate_id: envelope.candidates[0].candidate_id };
    const token = governor.issue(selection, envelope.bounded_set_revision)!;
    governor.invalidate(event);
    expect(governor.issue(selection, envelope.bounded_set_revision)).toBeNull();
    expect(governor.consume(token)).toBeNull();
  }
});

test('state changes are re-read before execution even without an explicit notification', () => {
  for (const mutate of [
    (env: AgencyEnvironment) => { env.journey.currentStopId = 'another-stop'; },
    (env: AgencyEnvironment) => { env.journey.interruptionState.isInterrupted = true; },
    (env: AgencyEnvironment) => { env.validEvidenceIds = []; },
    (env: AgencyEnvironment) => { env.satisfiedPreconditions = []; },
    (env: AgencyEnvironment) => { env.policyCapabilities = []; },
  ]) {
    const env = environment();
    const governor = createAgencyEnvelope(() => env);
    const envelope = governor.refresh();
    const token = governor.issue({ selected_candidate_id: 'move:explain' }, envelope.bounded_set_revision)!;
    mutate(env);
    expect(governor.consume(token)).toBeNull();
  }
});

test('a disappearing spatial target or semantic destination invalidates execution', () => {
  for (const navigation of [false, true]) {
    const binding: AgencyBinding = { ...explanation, binding_id: 'show', choreography: navigation ? 'NAVIGATE_TO' : 'GUIDE_TO',
      ...(navigation ? { semantic_destination: 'DETAILS' } : { semantic_target: 'FEATURE_CONTROL' }) };
    const env = environment([binding]);
    const governor = createAgencyEnvelope(() => env);
    const envelope = governor.refresh();
    const token = governor.issue({ selected_candidate_id: 'move:show' }, envelope.bounded_set_revision)!;
    if (navigation) env.destinations = {}; else env.spatialTargets = {};
    expect(governor.consume(token)).toBeNull();
    expect(governor.refresh().candidates).toEqual([]);
  }
});

test('permission tier is independent of action class and COMMIT always requires explicit confirmation', () => {
  const prepare = { ...explanation, binding_id: 'prepare', permission_tier: 'PREPARE' as const };
  const commit = { ...explanation, binding_id: 'commit', permission_tier: 'COMMIT' as const };
  const env = environment([prepare, commit]);
  const governor = createAgencyEnvelope(() => env);
  expect(governor.refresh().candidates).toHaveLength(0);
  env.permissionTiers.push('PREPARE', 'COMMIT');
  expect(governor.refresh().candidates.map(move => move.candidate_id)).toEqual(['move:prepare']);
  env.confirmations.push('commit');
  expect(governor.refresh().candidates).toHaveLength(2);
  const revision = governor.refresh().bounded_set_revision;
  const token = governor.issue({ selected_candidate_id: 'move:commit' }, revision)!;
  env.confirmations = [];
  expect(governor.consume(token)).toBeNull();
});

test('token forgery, cross-envelope use, return-to-position replay, and duplicate grants are rejected', () => {
  const env = environment();
  const first = createAgencyEnvelope(() => env);
  const other = createAgencyEnvelope(() => env);
  const envelope = first.refresh();
  const token = first.issue({ selected_candidate_id: 'move:explain' }, envelope.bounded_set_revision)!;
  expect(first.consume({ ...token, governed_position: 999 })).toBeNull();
  expect(other.consume(token)).toBeNull();
  first.invalidate('position'); // moved away and returned to the same chapter/stop
  expect(first.consume(token)).toBeNull();
  const fresh = first.refresh();
  const a = first.issue({ selected_candidate_id: 'move:explain' }, fresh.bounded_set_revision)!;
  const b = first.issue({ selected_candidate_id: 'move:explain' }, fresh.bounded_set_revision)!;
  expect(first.consume(a)).toBeNull();
  expect(first.consume(b)).not.toBeNull();
  expect(first.issue({ selected_candidate_id: 'move:explain' }, fresh.bounded_set_revision)).toBeNull();
});

test('question candidates reference registry topology and remain optional beside a non-question', () => {
  const question: AgencyBinding = { ...explanation, binding_id: 'refine', cognitive_action: 'REFINE', pattern_id: 'NOC_21', decision_dimension: 'CONSTRAINT_DISCOVERY' };
  const env = environment([explanation, question]);
  const governor = createAgencyEnvelope(() => env);
  expect(governor.refresh().vectors.LEGAL_PATTERNS).toEqual(['NOC_21']);
  expect(governor.refresh().candidates).toHaveLength(2);
  env.acquisition.confidenceByDimension.CONSTRAINT_DISCOVERY = 1;
  expect(governor.refresh().vectors.LEGAL_PATTERNS).toEqual([]);
  expect(governor.refresh().candidates).toHaveLength(1);
});

test('Kmax bounds the active candidate map before constructing any cognition payload', () => {
  const env = environment(Array.from({ length: 40 }, (_, index) => ({ ...explanation, binding_id: `explain-${index}` })));
  env.budget = { ...AGENCY_BUDGET, maxCandidates: 3 };
  const governor = createAgencyEnvelope(() => env);
  const envelope = governor.refresh();
  expect(envelope.candidates).toHaveLength(3);
  expect(governor.issue({ selected_candidate_id: 'move:explain-39' }, envelope.bounded_set_revision)).toBeNull();
  expect(boundedAgencyInput(envelope, 'a'.repeat(100000), 'b'.repeat(100000), env.budget).payload.visitor_context).toHaveLength(1500);
  expect(boundedAgencyInput(envelope, '', '', env.budget).metrics.kmax).toBe(3);
  expect(() => boundedAgencyInput(envelope, '', '', { ...env.budget!, maxCandidates: 1 })).toThrow('Kmax');
  expect(() => boundedAgencyInput(envelope, '', '', { ...env.budget!, maxPayloadBytes: 10 })).toThrow('budget');
});

test('schema validation rejects raw DOM authority and arbitrary action/choreography fields', () => {
  for (const bad of [
    { ...explanation, selector: '#checkout' }, { ...explanation, x: 50, y: 100 },
    { ...explanation, cognitive_action: 'BUY_ALL' }, { ...explanation, choreography: 'EXECUTE_JS' },
    { ...explanation, permission_tier: 'ROOT' }, { ...explanation, evidence_basis: ['site'].concat(Array(40).fill('fake')) },
    { ...explanation, permission_tier: ['OBSERVE'] }, { ...explanation, choreography: ['PING'] },
  ]) expect(validAgencyBinding(bad)).toBe(false);
});

test('a scanned checkout label does not grant execution permission or policy approval', () => {
  const checkout: AgencyBinding = { ...explanation, binding_id: 'CHECKOUT_PRIMARY', site_action: 'START_CHECKOUT', permission_tier: 'COMMIT' };
  const env = environment([checkout]);
  const governor = createAgencyEnvelope(() => env);
  expect(governor.refresh().candidates).toEqual([]);
  env.permissionTiers.push('COMMIT');
  env.confirmations.push('CHECKOUT_PRIMARY');
  env.policyCapabilities = [];
  expect(governor.refresh().candidates).toEqual([]);
  env.policyCapabilities.push('CHECKOUT_PRIMARY');
  const envelope = governor.refresh();
  const token = governor.issue({ selected_candidate_id: 'move:CHECKOUT_PRIMARY' }, envelope.bounded_set_revision)!;
  env.permissionTiers = ['OBSERVE'];
  expect(governor.consume(token)).toBeNull();
});

test('a destination cannot execute with expired evidence for its live target', () => {
  const env = environment([{ ...explanation, binding_id: 'navigate', choreography: 'NAVIGATE_TO', semantic_destination: 'DETAILS' }]);
  env.spatialTargets.FEATURE_CONTROL.evidenceId = 'expired';
  expect(createAgencyEnvelope(() => env).refresh().candidates).toEqual([]);
});
