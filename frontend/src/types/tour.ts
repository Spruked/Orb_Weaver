/** Stable machine identity and human-readable cognition context. */
export interface TourConcept {
  id: string;
  description: string;
  label?: string;
}

/** One real DOM stop; the controller verifies its required concepts. */
export interface TourStop {
  id: string;
  sectionDomSelector: string;
  purpose: string;
  mustUnderstand: TourConcept[];
  presentationGuidance?: string;
  avoid?: string[];
}

export type TourDecisionAction =
  | "RUN_PREFLIGHT_NOW"
  | "DEFER_PREFLIGHT";

export interface TourDecisionOption {
  label: string;
  action: TourDecisionAction;
}

export interface TourDecisionConfig {
  actionKey: string;
  options: TourDecisionOption[];
}

/** Ordered stops and deterministic chapter structure belong to the controller. */
export interface TourChapter {
  id: string;
  title?: string;
  chapterNumber: number;
  purpose: string;
  stops: TourStop[];
  /** Chapter-wide instructional objectives. */
  mustUnderstand: TourConcept[];
  avoid: string[];
  /** Presentation objectives for cognition, without scripted narration. */
  presentationGuidance?: string[];
  nextChapterId: string | null;
  isDecisionNode?: boolean;
  decisionConfig?: TourDecisionConfig;
}

/** Weaver supplies an exact excerpt from his speech, not a completion claim. */
export interface CoveredConcept {
  concept_id: string;
  supporting_excerpt: string;
}

/** Weaver's conversational evidence; the controller later verifies coverage. */
export interface ChapterEvaluation {
  spoken_output: string;
  covered_concepts: CoveredConcept[];
  detected_visitor_intent?: string | null;
  suggested_transition?: string | null;
}

export type TourPreflightStatus =
  | "NOT_STARTED"
  | "DEFERRED"
  | "RUNNING"
  | "COMPLETED_UNREVIEWED"
  | "COMPLETED_REVIEWED";
