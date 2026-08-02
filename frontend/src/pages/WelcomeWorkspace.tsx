import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ApiError,
  api,
  AuditDelta,
  CrawlJob,
  Customer,
  OrbsAllowedAction,
  OrbsGuestMergeResult,
  OrbsStageSnapshot,
} from '../services/api';
import { trackOnboardingEvent } from '../services/analytics';
import {
  clearMergedGuestReference,
  currentGuestReference,
  mergeIdempotencyKey,
} from '../onboarding/guestOnboarding';
import CrawlChangeSummary from '../components/CrawlChangeSummary';
import OrbAssemblyStatus from '../components/OrbAssemblyStatus';
import AuditChangeSummary from '../components/AuditChangeSummary';
import { canonicalOrbBaseUrl, setActiveOrbProjectContext } from '../orb/activeProjectContext';
import './Onboarding.css';

interface WelcomeWorkspaceProps {
  customer: Customer;
  initialMergeResult?: OrbsGuestMergeResult;
  initialMergeError?: string;
}

const TARGETS: Record<string, string> = {
  run_preflight: 'welcome-run-preflight',
  explore_orbs_packages: 'welcome-explore-packages',
  open_dashboard: 'welcome-open-dashboard',
  visit_orb_marketplace: 'welcome-marketplace',
};

const EVENT_BY_ACTION = {
  run_preflight: 'preflight_selected',
  explore_orbs_packages: 'packages_selected',
  open_dashboard: 'dashboard_selected',
  visit_orb_marketplace: 'marketplace_selected',
} as const;

function destination(action: OrbsAllowedAction) {
  if (!action.destination_verified || !action.destination_route?.startsWith('/')) return null;
  return action.destination_route;
}

const WelcomeWorkspace: React.FC<WelcomeWorkspaceProps> = ({
  customer,
  initialMergeResult,
  initialMergeError = '',
}) => {
  const navigate = useNavigate();
  const [snapshot, setSnapshot] = useState<OrbsStageSnapshot | null>(initialMergeResult?.fresh_snapshot || null);
  const [loading, setLoading] = useState(!initialMergeResult);
  const [workingAction, setWorkingAction] = useState('');
  const [error, setError] = useState(initialMergeError);
  const [latestCrawl, setLatestCrawl] = useState<CrawlJob | null>(null);
  const [auditDelta, setAuditDelta] = useState<AuditDelta | null>(null);

  const loadProjectEvidence = useCallback(async (projectId: string) => {
    try {
      const dashboard = await api.getCombinedDashboard(projectId);
      setLatestCrawl(dashboard.latest_crawl || null);
      setAuditDelta(dashboard.audit_delta || null);
      if (dashboard.project?.domain) {
        setActiveOrbProjectContext({
          project_id: String(dashboard.project.id || projectId),
          canonical_domain: dashboard.project.domain,
          canonical_base_url: canonicalOrbBaseUrl(dashboard.project.domain),
          selected_crawl_job_id: dashboard.latest_crawl?.id || dashboard.project.latest_crawl_id || null,
          active_customer_route: '/',
        });
      }
    } catch {
      setLatestCrawl(null);
      setAuditDelta(null);
    }
  }, []);

  const recoverAuthoritativeState = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const guestSessionId = currentGuestReference();
      if (guestSessionId) {
        const result = await api.mergeOrbsGuestSession(guestSessionId, {
          schema: 'orb_weaver.orbs_guest_merge_request.v1',
          guest_session_id: guestSessionId,
          idempotency_key: mergeIdempotencyKey(guestSessionId),
          project_display_name: customer.business_name,
        });
        clearMergedGuestReference(guestSessionId);
        setSnapshot(result.fresh_snapshot);
        void loadProjectEvidence(result.fresh_snapshot.project_id);
        trackOnboardingEvent('guest_merge_completed', { outcome: result.merge_status });
        trackOnboardingEvent('onboarding_completed', { outcome: 'recovered' });
        return;
      }

      const requestedProject = new URLSearchParams(window.location.search).get('project');
      if (requestedProject) {
        const fresh = await api.getOrbsStage(requestedProject);
        setSnapshot(fresh);
        void loadProjectEvidence(fresh.project_id);
        return;
      }

      const projects = await api.listProjects();
      const latest = [...projects].sort((left, right) =>
        String(right.created_at || '').localeCompare(String(left.created_at || ''))
      )[0];
      if (!latest) throw new Error('No website project is attached to this account yet.');
      const fresh = await api.getOrbsStage(String(latest.id));
      setSnapshot(fresh);
      void loadProjectEvidence(fresh.project_id);
    } catch (caught) {
      const message = caught instanceof ApiError ? caught.message : caught instanceof Error ? caught.message : 'Unable to load the authoritative project state.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [customer.business_name, loadProjectEvidence]);

  useEffect(() => {
    if (initialMergeResult) {
      clearMergedGuestReference(initialMergeResult.guest_session_id);
      void loadProjectEvidence(initialMergeResult.fresh_snapshot.project_id);
      setLoading(false);
      return;
    }
    void recoverAuthoritativeState();
  }, [initialMergeResult, recoverAuthoritativeState, loadProjectEvidence]);

  const invoke = async (action: OrbsAllowedAction) => {
    if (!snapshot) return;
    const verifiedDestination = destination(action);
    if (!verifiedDestination) {
      setError('The Stage Governor did not provide a verified destination for this action.');
      return;
    }
    if (action.confirmation_required && !window.confirm(`Confirm: ${action.display_label}?`)) return;

    setWorkingAction(action.name);
    setError('');
    try {
      const idempotencyKey = window.crypto.randomUUID();
      const fresh = await api.submitOrbsStageAction(snapshot.project_id, {
        project_id: snapshot.project_id,
        build_order_id: snapshot.build_order_id,
        action: action.name,
        expected_stage: snapshot.current_stage,
        snapshot_version: snapshot.snapshot_version,
        inputs: {},
        ...(action.confirmation_required ? {
          confirmation_evidence: {
            confirmed: true,
            project_id: snapshot.project_id,
            action_name: action.name,
            snapshot_version: snapshot.snapshot_version,
            confirmed_at: new Date().toISOString(),
            method: 'explicit_browser_confirmation',
            statement_hash: idempotencyKey,
          },
        } : {}),
      }, idempotencyKey);
      setSnapshot(fresh);
      void loadProjectEvidence(fresh.project_id);
      const eventName = EVENT_BY_ACTION[action.name as keyof typeof EVENT_BY_ACTION];
      if (eventName) trackOnboardingEvent(eventName, { action: action.name });
      navigate(verifiedDestination);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The Stage Governor rejected this action.');
      try {
        setSnapshot(await api.getOrbsStage(snapshot.project_id));
      } catch {
        // Keep the last valid snapshot visible while the customer retries.
      }
    } finally {
      setWorkingAction('');
    }
  };

  if (loading && !snapshot) {
    return <section className="welcome-workspace"><div className="welcome-loading">Weaver is restoring your authoritative workspace…</div></section>;
  }

  if (!snapshot) {
    return (
      <section className="welcome-workspace">
        <div className="welcome-error-panel" role="alert">
          <p>{error || 'The project merge is not complete.'}</p>
          <button id="welcome-retry-merge" data-orb-target="retry-project-merge" type="button" onClick={recoverAuthoritativeState}>Retry Project Merge</button>
        </div>
      </section>
    );
  }

  const onboarding = snapshot.approved_stage_evidence.onboarding as Record<string, unknown> | null;
  const activateWeaver = () => {
    const globalWeaver = document.querySelector<HTMLButtonElement>('.ow-v2-orb-body');
    globalWeaver?.click();
  };
  return (
    <section className="welcome-workspace" aria-labelledby="welcome-title">
      <div className="welcome-hero">
        <div>
          <p className="welcome-eyebrow">PROJECT-BOUND GUIDED ONBOARDING</p>
          <h1 id="welcome-title">Welcome to Orb Weaver</h1>
          <p>Your Orb Weaver workspace is ready, and I carried your website and original goal into the project. The next available step is Preflight.</p>
        </div>
        <button type="button" className="welcome-orb" onClick={activateWeaver} aria-label="Activate Weaver voice guidance"><span /></button>
      </div>

      <div className="welcome-grid">
        <article className="welcome-project-card">
          <p className="welcome-card-label">YOUR FIRST WEBSITE PROJECT</p>
          <h2>{snapshot.project_display_name}</h2>
          <dl>
            <div><dt>Customer</dt><dd>{customer.full_name}</dd></div>
            <div><dt>Business</dt><dd>{customer.business_name}</dd></div>
            <div><dt>Current stage</dt><dd>{snapshot.current_stage.replace(/_/g, ' ')}</dd></div>
            <div><dt>Status</dt><dd>{snapshot.stage_status.replace(/_/g, ' ')}</dd></div>
            {onboarding?.landing_intent ? <div><dt>Original goal</dt><dd>{String(onboarding.landing_intent).replace(/_/g, ' ')}</dd></div> : null}
            {onboarding?.selected_tier_interest ? <div><dt>Package interest</dt><dd>{String(onboarding.selected_tier_interest)}</dd></div> : null}
          </dl>
        </article>

        <aside className="welcome-next-card">
          <p className="welcome-card-label">WEAVER · VERIFIED NEXT ACTIONS</p>
          <h2>Start with technical evidence</h2>
          <p>Preflight checks the site before any crawl, audit, recommendation, or purchase decision. These actions come directly from the Stage Governor.</p>
          <div className="welcome-actions">
            {snapshot.allowed_actions.map((action, index) => (
              <button
                key={action.name}
                id={TARGETS[action.name] || `welcome-action-${action.name}`}
                data-orb-target={TARGETS[action.name] || action.name}
                type="button"
                className={index === 0 ? 'primary' : 'secondary'}
                disabled={Boolean(workingAction) || !destination(action)}
                onClick={() => void invoke(action)}
              >
                {workingAction === action.name ? 'Working…' : action.display_label}
              </button>
            ))}
          </div>
          {error ? <p className="welcome-inline-error" role="alert">{error}</p> : null}
        </aside>
      </div>

      <div className="mt-6 grid gap-4">
        <OrbAssemblyStatus assembly={latestCrawl?.assembly_status} compact />
        <CrawlChangeSummary crawl={latestCrawl} title="What changed in this workspace recrawl" />
        <AuditChangeSummary delta={auditDelta} />
      </div>
    </section>
  );
};

export default WelcomeWorkspace;
