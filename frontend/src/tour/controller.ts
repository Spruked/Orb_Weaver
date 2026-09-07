import type { ChapterEvaluation, TourChapter, TourConcept, TourStop } from '../types/tour';
import type { WebsiteJourneyStateV2 } from '../state/tourControllerStore';
import { getTourPosition, LANDING_TOUR_CHAPTERS } from './curriculum';
import { verifiedConceptIds } from './evaluator';

export function requiredConcepts(_chapter: TourChapter, stop: TourStop, state: WebsiteJourneyStateV2): TourConcept[] {
  const concepts = stop.mustUnderstand;
  const covered = new Set([...state.completedTourConceptIds, ...state.currentStopCoveredConceptIds]);
  return [...new Map(concepts.map(concept => [concept.id, concept])).values()].filter(concept => !covered.has(concept.id));
}

export function isTourDecisionReady(state: WebsiteJourneyStateV2): boolean {
  const position = getTourPosition(state.currentChapterId, state.currentStopId);
  return state.stage === 'LANDING_TOUR' && Boolean(position?.chapter.isDecisionNode) &&
    Boolean(position && requiredConcepts(position.chapter, position.stop, state).length === 0);
}

interface TourRuntime {
  read(): WebsiteJourneyStateV2 | null;
  save(state: WebsiteJourneyStateV2): void;
  verifySection(stop: TourStop, signal: AbortSignal): Promise<boolean>;
  demonstrate(chapter: TourChapter, stop: TourStop, signal: AbortSignal): Promise<boolean>;
  // Must resolve only after the same spoken_output finished playing.
  converse(chapter: TourChapter, stop: TourStop, missing: TourConcept[], signal: AbortSignal): Promise<ChapterEvaluation>;
}

const checkAbort = (signal: AbortSignal) => {
  if (signal.aborted) throw new DOMException('Tour interrupted', 'AbortError');
};

export async function runTourController(runtime: TourRuntime, signal: AbortSignal): Promise<'decision' | 'inactive'> {
  for (;;) {
    checkAbort(signal);
    let state = runtime.read();
    if (!state || state.stage !== 'LANDING_TOUR' || state.preflightStatus === 'DEFERRED' || state.interruptionState.isInterrupted) return 'inactive';
    const position = getTourPosition(state.currentChapterId, state.currentStopId);
    if (!position) throw new Error('This saved tour position is not available. Your progress has been preserved.');
    const { chapter, stop } = position;
    if (!await runtime.verifySection(stop, signal)) throw new Error('This tour section is unavailable. Your progress is saved; try continuing again.');
    checkAbort(signal);
    if (!await runtime.demonstrate(chapter, stop, signal)) throw new Error('The live guidance target could not be verified. Your tour position is saved.');
    checkAbort(signal);
    for (let attempt = 0; attempt < 2; attempt += 1) {
      const missing = requiredConcepts(chapter, stop, state);
      if (!missing.length) break;
      const evaluation = await runtime.converse(chapter, stop, missing, signal);
      checkAbort(signal);
      const current = runtime.read();
      if (!current || current.stage !== state.stage || current.currentChapterId !== chapter.id || current.currentStopId !== stop.id || current.interruptionState.isInterrupted) return 'inactive';
      state = { ...current, currentStopCoveredConceptIds: [...new Set([...current.currentStopCoveredConceptIds, ...verifiedConceptIds(evaluation, missing)])] };
      runtime.save(state);
    }
    if (requiredConcepts(chapter, stop, state).length) throw new Error('Weaver has more to explain here. Continue when you’re ready; your progress is saved.');
    checkAbort(signal);
    state = { ...state, completedTourConceptIds: [...new Set([...state.completedTourConceptIds, ...state.currentStopCoveredConceptIds])] };
    if (chapter.isDecisionNode) {
      runtime.save(state);
      return 'decision';
    }
    const nextStop = chapter.stops[chapter.stops.findIndex(item => item.id === stop.id) + 1];
    if (nextStop) {
      runtime.save({ ...state, currentStopId: nextStop.id, currentStopCoveredConceptIds: [] });
    } else {
      // The graph is authoritative; Weaver's suggested_transition is advisory only.
      const next = getTourChapterOpening(chapter.nextChapterId);
      if (!next) throw new Error('The next tour chapter is unavailable. Your progress has been preserved.');
      runtime.save({ ...state, currentChapterId: next.chapterId, currentStopId: next.stopId, currentStopCoveredConceptIds: [] });
    }
  }
}

function getTourChapterOpening(id: string | null) {
  const chapter = LANDING_TOUR_CHAPTERS.find(item => item.id === id);
  return chapter?.stops[0] ? { chapterId: chapter.id, stopId: chapter.stops[0].id } : null;
}
