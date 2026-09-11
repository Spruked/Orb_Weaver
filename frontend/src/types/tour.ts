/** Stable machine identity and human-readable cognition context. */
export interface TourConcept {
  id: string;
  description: string;
  label?: string;
  /** Meaning-bearing terms that must appear in proof of this concept. */
  coverageRequirements?: string[];
}

/** One real DOM stop; the controller verifies its required concepts. */
export interface TourStop {
  id: string;
  sectionDomSelector: string;
  purpose: string;
  mustUnderstand: TourConcept[];
  presentationGuidance?: string;
  avoid?: string[];
  engagementQuestion?: TourEngagementQuestion;
}

/** A bounded visitor choice. Its destinations are authored, never model-chosen. */
export interface TourEngagementQuestion {
  id: string;
  intent: string;
  prompt: string;
  options: Array<{
    id: string;
    /** Stable answer meaning. Only the governor may translate it to a route. */
    semanticCategory: TourSemanticCategory;
    keywords: string[];
  }>;
}

/** Bounded visitor-answer meanings; these are not navigation instructions. */
export type TourSemanticCategory =
  | 'SITE_DISCOVERY'
  | 'VERIFIED_GUIDANCE'
  | 'VISITOR_UNDERSTANDING'
  | 'VISITOR_ASSISTANCE'
  | 'DISCOVERY_FRICTION'
  | 'CONVERSION_FRICTION';

/** The only non-action routes a public Target One interaction may select. */
export type TourDestinationRoute = '/features' | '/lidar-guidance' | '/how-it-works' | '/preflight';

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
