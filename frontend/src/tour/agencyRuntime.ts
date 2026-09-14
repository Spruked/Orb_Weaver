/** One agency turn inside the existing tour scheduler and existing spatial runtime. */
import { api, authStore } from '../services/api';
import type { WebsiteOrbPageCapsule, WebsiteOrbPointerRecord, WebsiteOrbTtsResponse } from '../services/api';
import type { WebsiteJourneyStateV2 } from '../state/tourControllerStore';
import type { AgencyBinding, AgencyEnvironment, CandidateMove } from '../types/agency';
import type { DiscoveryCognitionAdapter, DiscoveryDimension, DiscoveryPattern } from '../types/discovery';
import { createAgencyEnvelope, eligibleDiscoveryPatterns, legalTourNavigationRoutes, resolveGovernedDestination } from './governor';
import { DISCOVERY_PATTERNS, discoveryPatternById } from './discovery/registry';
import { compileQuestion, interpretResponse } from './discovery/compiler';
import { engagementById } from './interaction';
import { getTourPosition } from './curriculum';
import { validateOrbPointerTarget } from '../orb/targetValidation';
import { AGENCY_BUDGET, boundedAgencyInput } from './agencyBudget';
import {
  activeAgencyExcursion,
  beginAgencyExcursion,
  consumeAgencyExcursionReturn,
  markAgencyExcursionArrived,
  patchAgencySessionCache,
  readAgencySessionCache,
  rememberAgencyEvidence,
} from './agencySessionCache';

interface TourAgencyHost {
  read(): WebsiteJourneyStateV2 | null;
  save(state: WebsiteJourneyStateV2): void;
  pointers(): WebsiteOrbPointerRecord[];
  capsule(): WebsiteOrbPageCapsule | null;
  targetUrl(): string;
  worldRevision(): number;
  speak(text: string, audio?: string | null, provider?: string | null): Promise<boolean>;
  guide(record: WebsiteOrbPointerRecord, signal: AbortSignal): Promise<boolean>;
  navigate(route: string): void;
  telemetry(name: string, data: Record<string, unknown>): void;
}

const quiet = { warn: () => undefined, info: () => undefined };
const lexicon = { slots: { host: { text: 'the website guide', evidenceId: 'capability:website_host' } } };

export function createTourAgencyRuntime(host: TourAgencyHost) {
  let positionRevision = 0;
  let visitorRevision = 0;
  let evidenceRevision = 0;
  let domRevision = 0;
  let permissionRevision = 0;
  let permissionIdentity: string | null = null;
  let lastPosition = '';
  let visitorContext = readAgencySessionCache().visitorContext;
  let requestedRoute: string | null = null;
  let busy = false;
  const check = (signal: AbortSignal) => { if (signal.aborted) throw new DOMException('Agency interrupted', 'AbortError'); };

  const observe = async (payload: Record<string, unknown>, signal?: AbortSignal) => {
    const result = await api.websiteOrbAgency('observe', payload, host.targetUrl(), signal);
    evidenceRevision += 1;
    if (typeof result.event_id === 'string') rememberAgencyEvidence(result.event_id);
    host.telemetry('agency_evidence_recorded', { eventId: result.event_id, source: payload.source });
  };

  const environment = (): AgencyEnvironment => {
    const journey = host.read();
    if (!journey) throw new Error('No active tour state');
    const position = JSON.stringify([journey.stage, journey.currentChapterId, journey.currentStopId, window.location.pathname]);
    if (lastPosition !== position) { lastPosition = position; positionRevision += 1; }
    const identity = authStore.getToken();
    if (identity !== permissionIdentity) { permissionIdentity = identity; permissionRevision += 1; }
    const route = window.location.pathname;
    const page = host.capsule();
    const pageIsCurrent = Boolean(page && new URL(page.current_url, host.targetUrl()).pathname === route);
    const section = getTourPosition(journey.currentChapterId, journey.currentStopId)?.stop;
    const sectionExists = Boolean(section && document.querySelector(section.sectionDomSelector));
    const pageEvidence = `page:${route}`;
    const activeExcursion = activeAgencyExcursion();
    const env: AgencyEnvironment = {
      journey, route, positionRevision, domRevision: domRevision + host.worldRevision(), visitorRevision, evidenceRevision, permissionRevision,
      universalCapabilities: [], scannedAffordances: [], liveAffordances: [], governedCapabilities: [], policyCapabilities: [],
      permissionTiers: ['OBSERVE', 'NAVIGATE'], confirmations: [], validEvidenceIds: ['capability:website_host'],
      satisfiedPreconditions: ['tour_active'], legalStageTransitions: [], destinations: {}, spatialTargets: {}, bindings: [],
      acquisition: { confidenceByDimension: {}, askedPatternIds: journey.interaction.askedQuestionIds,
        remainingAcquisitions: Math.max(0, 5 - (journey.interaction.agency?.acquisitions || 0)),
        availableCandidateActionIds: DISCOVERY_PATTERNS.flatMap(pattern => pattern.choices.filter(choice => choice.candidateAction.kind === 'EXPLAIN').map(choice => choice.candidateAction.id)),
      },
      budget: AGENCY_BUDGET,
    };
    for (const [id, answer] of Object.entries(journey.interaction.agency?.answers || {})) {
      const pattern = discoveryPatternById(id);
      if (pattern && pattern.choices.some(choice => choice.semanticOutput === answer.semanticOutput)) {
        env.acquisition.confidenceByDimension[pattern.dimension] = Math.max(env.acquisition.confidenceByDimension[pattern.dimension] || 0, answer.confidence);
      }
    }
    if (journey.stage !== 'LANDING_TOUR' || (!sectionExists && !pageIsCurrent)) return env;
    env.validEvidenceIds.push(pageEvidence);
    const add = (binding: AgencyBinding, scan: boolean, live: boolean, policy = true) => {
      env.bindings.push(binding);
      env.universalCapabilities.push(binding.binding_id);
      env.governedCapabilities.push(binding.binding_id);
      if (scan) env.scannedAffordances.push(binding.binding_id);
      if (live) env.liveAffordances.push(binding.binding_id);
      if (policy) env.policyCapabilities.push(binding.binding_id);
    };
    const common = { permission_tier: 'OBSERVE' as const, requires_confirmation: false, evidence_basis: [pageEvidence], preconditions: ['tour_active'] };
    add({ ...common, binding_id: 'explain-current', purpose: 'Explain the current context or clarify the visitor’s concern without asking a question.', cognitive_action: 'EXPLAIN', choreography: 'EXPLAIN_IN_PLACE' }, sectionExists || pageIsCurrent, true);
    const legacy = section?.engagementQuestion;
    if (legacy && !requestedRoute && !journey.interaction.pendingQuestionId && env.acquisition.remainingAcquisitions > 0) {
      add({ ...common, binding_id: `question:${legacy.id}`, pattern_id: legacy.id, purpose: legacy.intent, cognitive_action: 'DISCOVER', choreography: 'EXPLAIN_IN_PLACE' }, true, sectionExists);
    }
    for (const pattern of (requestedRoute ? [] : eligibleDiscoveryPatterns(journey, env.acquisition).slice(0, AGENCY_BUDGET.maxCandidates))) {
      add({ ...common, binding_id: `question:${pattern.id}`, pattern_id: pattern.id, decision_dimension: pattern.dimension,
        purpose: pattern.intent, cognitive_action: 'REFINE', choreography: 'EXPLAIN_IN_PLACE' }, true, true);
    }
    const allowedRoutes = legalTourNavigationRoutes(journey);
    for (const pointer of host.pointers().filter(item => item.page_route === route).slice(0, 60)) {
      const verified = validateOrbPointerTarget(pointer, { logger: quiet });
      if (!verified.ok) continue;
      const alias = pointer.target_id;
      const evidenceId = `pointer:${pointer.target_id}:${pointer.content_fingerprint}`;
      env.validEvidenceIds.push(evidenceId);
      env.spatialTargets[alias] = { targetId: pointer.target_id, evidenceId };
      if (env.bindings.filter(binding => binding.cognitive_action === 'DEMONSTRATE').length < AGENCY_BUDGET.maxCandidates) {
        add({ ...common, binding_id: `demonstrate:${alias}`, purpose: `Demonstrate ${pointer.meaning || alias} through verified guidance.`, cognitive_action: 'DEMONSTRATE',
          choreography: 'GUIDE_TO', semantic_target: alias, permission_tier: 'NAVIGATE', evidence_basis: [pageEvidence, evidenceId] }, true, true,
        pointer.runtime_policy?.may_point === true && pointer.runtime_policy?.requires_user_confirmation !== true);
      }
      const anchor = verified.element.closest('a[href]') as HTMLAnchorElement | null;
      if (activeExcursion || !anchor || pointer.runtime_policy?.may_navigate !== true || pointer.runtime_policy?.requires_user_confirmation === true) continue;
      const target = new URL(anchor.href, window.location.origin);
      if (target.origin !== window.location.origin || target.search || target.hash || !allowedRoutes.includes(target.pathname as any) || target.pathname === route) continue;
      if (requestedRoute && target.pathname !== requestedRoute) continue;
      const semantic = `destination:${alias}`;
      env.destinations[semantic] = { route: target.pathname, evidenceId, targetAlias: alias };
      add({ ...common, binding_id: `navigate:${alias}`, purpose: `View ${pointer.meaning || alias} on its verified page.`, cognitive_action: 'TRANSITION',
        choreography: 'NAVIGATE_TO', semantic_destination: semantic, permission_tier: 'NAVIGATE', evidence_basis: [pageEvidence, evidenceId] }, true, true);
    }
    return env;
  };
  const authority = createAgencyEnvelope(environment);

  const provider = (signal: AbortSignal): DiscoveryCognitionAdapter => ({
    compile_question: async input => (await api.websiteOrbAgency('compile_question', input, host.targetUrl(), signal)).result,
    classify_response: async input => (await api.websiteOrbAgency('classify_response', input, host.targetUrl(), signal)).result,
  });

  const turn = async (signal: AbortSignal): Promise<'continue' | 'awaiting_visitor'> => {
    if (busy) return 'awaiting_visitor';
    busy = true;
    try {
      check(signal);
      const startingState = host.read();
      if (!startingState) return 'continue';
      const arrived = markAgencyExcursionArrived(window.location.pathname, startingState);
      if (arrived) {
        host.telemetry('agency_excursion_arrived', {
          excursion_id: arrived.excursionId, destination_route: arrived.destinationRoute,
          origin_route: arrived.origin.route,
        });
      }
      const envelope = authority.refresh();
      if (!envelope.candidates.length) return 'continue';
      host.telemetry('agency_envelope', envelope as unknown as Record<string, unknown>);
      const currentEnv = environment();
      const cache = readAgencySessionCache();
      const activeExcursion = activeAgencyExcursion();
      const working = boundedAgencyInput(envelope, visitorContext, host.capsule()?.page_summary || '', AGENCY_BUDGET, {
        confidence: currentEnv.acquisition.confidenceByDimension,
        beliefs: Object.entries(currentEnv.journey.interaction.agency?.answers || {}).slice(-8).map(([pattern, answer]) => ({ pattern, ...answer })),
        coverage: currentEnv.journey.completedTourConceptIds.slice(-24),
        recent_interaction: currentEnv.journey.interaction.recentWeaverStatements.slice(-3).map(text => text.slice(0, 400)),
        active_permissions: currentEnv.permissionTiers,
        acquisitions_remaining: currentEnv.acquisition.remainingAcquisitions,
        recent_evidence_ids: cache.recentEvidenceIds,
        active_excursion: activeExcursion ? {
          purpose: activeExcursion.purpose,
          origin_route: activeExcursion.origin.route,
          destination_route: activeExcursion.destinationRoute,
          status: activeExcursion.status,
        } : null,
      });
      host.telemetry('agency_working_set', working.metrics);
      const response = await api.websiteOrbAgency('choose_candidate', working.payload, host.targetUrl(), signal);
      check(signal);
      let authorization = authority.issue(response.result, envelope.bounded_set_revision);
      if (!authorization) throw new Error('The legal context changed; Weaver will recheck before acting.');
      const selected = envelope.candidates.find(move => move.candidate_id === authorization!.candidate_id)!;
      patchAgencySessionCache({ boundedSetRevision: envelope.bounded_set_revision, activeCandidateId: selected.candidate_id, visitorContext });
      host.telemetry('agency_candidate_selected', { candidate_id: selected.candidate_id, bounded_set_revision: envelope.bounded_set_revision });
      let text = '';
      let audio: Pick<WebsiteOrbTtsResponse, 'tts_audio_url' | 'tts_provider'> | null = null;
      if (selected.pattern_id) {
        const pattern = discoveryPatternById(selected.pattern_id);
        text = pattern ? (await compileQuestion(pattern, lexicon, provider(signal), [visitorContext], 15000)).spokenQuestion
          : engagementById(selected.pattern_id)?.prompt || '';
        if (!text) throw new Error('The selected question has no validated rendering');
        audio = await api.websiteOrbTts(text, signal);
      } else if (selected.cognitive_action === 'EXPLAIN') {
        const result = await api.websiteOrbText(visitorContext || 'Explain the current page briefly using the verified site context.', true, signal, {
          target_url: host.targetUrl(), experience: { phase: 'understanding', objective: 'Give one relevant explanation without asking a question, claiming an action or announcing navigation.', verification_state: 'not_applicable' },
        });
        text = result.spoken_output;
        audio = result;
      }
      check(signal);
      // Compilation and TTS can take time. All facts are read again before execution.
      authorization = authority.issue(response.result, envelope.bounded_set_revision);
      if (!authorization) throw new Error('The selected move expired while preparing speech. Your place is saved.');
      let awaiting = false;
      const executed = await authority.execute(authorization, async move => {
        check(signal);
        if (move.pattern_id) {
          if (!await host.speak(text, audio?.tts_audio_url, audio?.tts_provider)) return false;
          check(signal);
          const state = host.read()!;
          host.save({ ...state, interaction: { ...state.interaction,
            pendingQuestionId: move.pattern_id, askedQuestionIds: [...new Set([...state.interaction.askedQuestionIds, move.pattern_id])],
            eligibleDestinationRoutes: legalTourNavigationRoutes(state),
            eligibleDestinationScope: { questionId: move.pattern_id, stage: state.stage, chapterId: state.currentChapterId, stopId: state.currentStopId },
            agency: { answers: state.interaction.agency?.answers || {}, acquisitions: (state.interaction.agency?.acquisitions || 0) + 1 },
          } });
          awaiting = true;
          return true;
        }
        if (move.choreography === 'GUIDE_TO') {
          const target = environment().spatialTargets[move.semantic_target!];
          const pointer = host.pointers().find(item => item.target_id === target?.targetId);
          if (!pointer || !validateOrbPointerTarget(pointer, { logger: quiet }).ok) return false;
          return host.guide(pointer, signal);
        }
        if (move.choreography === 'NAVIGATE_TO') {
          const destination = environment().destinations[move.semantic_destination!];
          if (!destination) return false;
          const state = host.read()!;
          const contract = beginAgencyExcursion({
            candidateId: move.candidate_id,
            boundedSetRevision: move.bounded_set_revision,
            purpose: move.purpose,
            origin: {
              stage: state.stage,
              chapterId: state.currentChapterId,
              stopId: state.currentStopId,
              route: window.location.pathname,
            },
            destinationRoute: destination.route,
            semanticDestination: move.semantic_destination!,
          });
          if (!contract) return false;
          host.save({ ...state, interaction: { ...state.interaction, activeDestinationRoute: destination.route as any } });
          const persisted = host.read();
          const persistedContract = activeAgencyExcursion();
          if (!persisted || persisted.interaction.activeDestinationRoute !== destination.route ||
            persistedContract?.excursionId !== contract.excursionId) return false;
          host.telemetry('agency_excursion_started', {
            excursion_id: contract.excursionId,
            candidate_id: move.candidate_id,
            origin_route: contract.origin.route,
            destination_route: contract.destinationRoute,
          });
          host.navigate(destination.route);
          requestedRoute = null;
          awaiting = true;
          return true; // Route request only; arrival and destination work are reverified after remount.
        }
        return host.speak(text, audio?.tts_audio_url, audio?.tts_provider);
      });
      await observe({ source: selected.cognitive_action === 'DEMONSTRATE' ? 'DEMONSTRATION_RESULT' : 'LIVE_BEHAVIOR',
        candidate_id: selected.candidate_id, bounded_set_revision: envelope.bounded_set_revision,
        outcome: executed ? (selected.choreography === 'NAVIGATE_TO' ? 'navigation_requested' : 'completed') : 'blocked',
        pattern_id: selected.pattern_id, spoken_output: text,
      });
      host.telemetry('agency_execution', { candidate_id: selected.candidate_id, executed });
      if (!executed) throw new Error('The selected move could not be verified. Your place is saved.');

      if (selected.choreography !== 'NAVIGATE_TO') {
        const active = activeAgencyExcursion();
        const current = host.read();
        const hasDemonstrationCandidate = envelope.candidates.some(move => move.cognitive_action === 'DEMONSTRATE');
        const destinationWorkComplete = selected.cognitive_action === 'DEMONSTRATE' ||
          (!hasDemonstrationCandidate && selected.cognitive_action === 'EXPLAIN');
        if (active && current && active.status === 'ACTIVE' && destinationWorkComplete &&
          window.location.pathname === active.destinationRoute) {
          const resume = consumeAgencyExcursionReturn(active.excursionId, window.location.pathname, current);
          if (resume) {
            host.save({ ...current, interaction: { ...current.interaction,
              activeDestinationRoute: null,
              visitedRoutes: [...new Set([...current.interaction.visitedRoutes, resume.destinationRoute])],
            } });
            patchAgencySessionCache({ boundedSetRevision: null, activeCandidateId: null, visitorContext });
            host.telemetry('agency_excursion_resuming', {
              excursion_id: resume.excursionId,
              return_route: resume.origin.route,
              stage: resume.origin.stage,
              chapter: resume.origin.chapterId,
              stop: resume.origin.stopId,
            });
            authority.invalidate('route');
            host.navigate(resume.origin.route);
            awaiting = true;
          }
        }
      }
      patchAgencySessionCache({ activeCandidateId: null, visitorContext });
      return awaiting ? 'awaiting_visitor' : 'continue';
    } finally { busy = false; }
  };

  const answer = async (transcript: string, signal: AbortSignal): Promise<boolean> => {
    const state = host.read();
    if (!state || state.stage !== 'LANDING_TOUR') return false;
    visitorContext = transcript;
    patchAgencySessionCache({ visitorContext });
    visitorRevision += 1;
    authority.invalidate('visitor');
    await observe({ source: 'VISITOR_DECLARATION', text: transcript, question_id: state.interaction.pendingQuestionId }, signal);
    const id = state.interaction.pendingQuestionId;
    if (id) {
      const canonical = discoveryPatternById(id);
      const legacy = engagementById(id);
      const pattern = canonical || (legacy ? { id, confidenceTarget: 0.8, choices: legacy.options.map(option => ({ semanticOutput: option.semanticCategory })) } as DiscoveryPattern : null);
      if (!pattern) return false;
      const interpretation = await interpretResponse(pattern, transcript, provider(signal), 30000);
      if (!interpretation || interpretation.categories.length !== 1 || interpretation.categories[0].confidence < pattern.confidenceTarget) return true;
      const category = interpretation.categories[0];
      await observe({ source: 'INFERRED', question_id: id, ...category }, signal);
      const current = host.read();
      if (!current || current.interaction.pendingQuestionId !== id || current.currentChapterId !== state.currentChapterId || current.currentStopId !== state.currentStopId) return true;
      // Resuming after the visitor's answer preserves the exact pending position.
      const resumed = { ...current, interruptionState: { isInterrupted: false, interruptedAtChapterId: null, interruptedAtStopId: null } };
      if (legacy) {
        const destination = resolveGovernedDestination(resumed, legacy, category.semanticOutput as any);
        if (!destination) return true;
        requestedRoute = destination;
        // Routing is selected from a newly verified coherent envelope below.
        visitorContext += `\nVisitor selected the governed direction ${category.semanticOutput}.`;
        patchAgencySessionCache({ visitorContext });
      }
      host.save({ ...resumed, interaction: { ...resumed.interaction,
        pendingQuestionId: null, eligibleDestinationRoutes: [], eligibleDestinationScope: null,
        answerSignals: { ...resumed.interaction.answerSignals, [id]: category.semanticOutput },
        agency: { answers: { ...resumed.interaction.agency?.answers, [id]: { semanticOutput: category.semanticOutput, confidence: category.confidence } }, acquisitions: resumed.interaction.agency?.acquisitions || 1 },
      } });
    } else if (state.interruptionState.isInterrupted) {
      host.save({ ...state, interruptionState: { isInterrupted: false, interruptedAtChapterId: null, interruptedAtStopId: null } });
    }
    await turn(signal);
    return true;
  };

  return { turn, answer, authority,
    invalidatePosition: () => { positionRevision += 1; authority.invalidate('position'); },
    invalidateDOM: () => { domRevision += 1; authority.invalidate('dom'); },
  };
}
