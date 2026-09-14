import type { TourJourneyStage } from '../state/tourControllerStore';

/** Decision dimensions are independent of the existing journey-stage machine. */
export const DISCOVERY_DIMENSIONS = [
  'GOAL_DISCOVERY', 'VISITOR_STATE_DISCOVERY', 'FRICTION_DISCOVERY',
  'PRIORITY_SELECTION', 'CONSTRAINT_DISCOVERY', 'CAPABILITY_SELECTION',
  'PROOF_SELECTION', 'COMMERCIAL_FIT_DISCOVERY', 'COMMITMENT_NEXT_STEP',
] as const;
export type DiscoveryDimension = typeof DISCOVERY_DIMENSIONS[number];

export type CandidateActionKind =
  | 'EXPLAIN' | 'DEMONSTRATE' | 'REVIEW_COMMERCIAL_FIT'
  | 'REQUEST_SITE_SCAN' | 'REQUEST_CONFIGURATION' | 'REVIEW_IMPLEMENTATION';

/** A proposal for the existing Governor to evaluate, never an executable grant. */
export interface DiscoveryCandidateAction {
  id: string;
  kind: CandidateActionKind;
  topic: string;
  requiresExplicitConsent: boolean;
  requiresLiveVerification: boolean;
}

export interface DiscoveryPattern {
  id: string;
  sourceNumber: number;
  dimension: DiscoveryDimension;
  intent: string;
  choices: Array<{
    semanticOutput: string;
    fallbackLabel: string;
    candidateAction: DiscoveryCandidateAction;
  }>;
  requiredLexicalSlots: string[];
  legalStages: TourJourneyStage[];
  requiredDimensions: DiscoveryDimension[];
  confidenceTarget: number;
  informationGainWeight: number;
  convergenceWeight: number;
  generationConstraints: {
    choiceCount: number;
    preserveOrder: boolean;
    allowAdditionalBranches: boolean;
    allowYesNoExit: boolean;
  };
  fallbackStem: string;
  fallbackRendering: string;
}

/** Slots and label alternatives must come from reviewed Site World semantics. */
export interface DiscoveryLexicon {
  slots: Readonly<Record<string, { text: string; evidenceId: string }>>;
  choiceAliases?: Readonly<Record<string, ReadonlyArray<{ text: string; evidenceId: string }>>>;
}

/** This provider-neutral response has no route, permission, or speech field. */
export interface CompiledChoiceProposal {
  patternId: string;
  choices: Array<{ semanticOutput: string; label: string }>;
}

export interface InterpretedResponse {
  patternId: string;
  categories: Array<{ semanticOutput: string; confidence: number; supportingExcerpt: string }>;
}

export interface DiscoveryCognitionAdapter {
  compile_question(input: {
    pattern: DiscoveryPattern;
    lexicon: DiscoveryLexicon;
    relevantContext: readonly string[];
  }): Promise<unknown>;
  classify_response(input: {
    patternId: string;
    allowedSemanticOutputs: readonly string[];
    visitorResponse: string;
  }): Promise<unknown>;
}
