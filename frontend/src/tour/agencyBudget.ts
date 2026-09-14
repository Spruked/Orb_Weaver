import type { AgencyBudget, AgencyEnvelope } from '../types/agency';

const configured = (value: string | undefined, fallback: number, low: number, high: number) => {
  if (value === undefined) return fallback;
  const result = Number(value);
  if (!Number.isInteger(result) || result < low || result > high) throw new Error('Invalid Agency Envelope budget configuration');
  return result;
};

/** Kmax and B are operational bounds, not claims of constant-time inference/storage. */
export const AGENCY_BUDGET: AgencyBudget = Object.freeze({
  maxCandidates: configured(process.env.REACT_APP_AGENCY_KMAX, 5, 1, 64),
  maxPayloadBytes: configured(process.env.REACT_APP_AGENCY_CONTEXT_MAX_BYTES, 32000, 4000, 128000),
  maxEvidenceItems: configured(process.env.REACT_APP_AGENCY_EVIDENCE_MAX_ITEMS, 8, 0, 32),
  maxEvidenceBytes: configured(process.env.REACT_APP_AGENCY_EVIDENCE_MAX_BYTES, 6000, 0, 32000),
});

export function agencyPayloadBytes(value: unknown): number {
  // TextEncoder is absent in some test environments; Blob uses browser UTF-8 encoding.
  return new Blob([JSON.stringify(value)]).size;
}

export function boundedAgencyInput(envelope: AgencyEnvelope, visitorContext: string, pageSummary: string, budget = AGENCY_BUDGET, workingState: {
  confidence?: Record<string, number>;
  beliefs?: Array<{ pattern: string; semanticOutput: string; confidence: number }>;
  coverage?: string[];
  recent_interaction?: string[];
  active_permissions?: string[];
  acquisitions_remaining?: number;
  recent_evidence_ids?: string[];
  active_excursion?: {
    purpose: string;
    origin_route: string;
    destination_route: string;
    status: 'PENDING_ARRIVAL' | 'ACTIVE';
  } | null;
} = {}) {
  if (envelope.candidates.length > budget.maxCandidates) throw new Error('Candidate count exceeds Kmax before cognition');
  const payload = {
    bounded_set_revision: envelope.bounded_set_revision,
    position: envelope.position,
    visitor_context: visitorContext.slice(-1500),
    current_page: pageSummary.slice(0, 1800),
    relevant_destinations: envelope.vectors.LEGAL_SEMANTIC_DESTINATIONS,
    current_targets: envelope.vectors.LEGAL_SPATIAL_TARGETS,
    working_state: workingState,
    candidates: envelope.candidates,
  };
  // Reserve evidence space. Neither the candidate object nor its branches are truncated.
  const bytes = agencyPayloadBytes(payload);
  if (bytes + budget.maxEvidenceBytes > budget.maxPayloadBytes) throw new Error('Active agency working set exceeds budget B');
  return { payload, metrics: { candidate_count: payload.candidates.length, kmax: budget.maxCandidates,
    working_set_bytes: bytes, evidence_reserve_bytes: budget.maxEvidenceBytes, budget_bytes: budget.maxPayloadBytes } };
}
