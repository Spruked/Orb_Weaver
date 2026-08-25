import React, { useEffect, useState } from 'react';
import { Activity, AlertTriangle, CheckCircle2, CircleDashed, Clock3, ShieldCheck } from 'lucide-react';
import { api, ScanAssemblyStatus, ScanAssemblyStage } from '../services/api';

const statusTone = (status: string) => {
  const normalized = status.toUpperCase();
  if (['COMPLETE', 'PASS', 'VERIFIED', 'VERIFIED_FULL', 'IDENTIFIED', 'DETECTED', 'VERIFIED_NOT_DETECTED'].includes(normalized)) return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  if (normalized === 'RUNNING') return 'border-blue-200 bg-blue-50 text-blue-700';
  if (normalized === 'FAILED' || normalized === 'FAIL') return 'border-red-200 bg-red-50 text-red-700';
  if (['BLOCKED', 'NEEDS_REVIEW', 'REVIEW_REQUIRED', 'REQUIRED', 'REQUIRES_VERIFICATION', 'NOT_RUN', 'PARTIAL', 'PARTIAL_ROUTE_CAP'].includes(normalized)) {
    return 'border-amber-200 bg-amber-50 text-amber-700';
  }
  return 'border-slate-200 bg-white text-slate-500';
};

const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
  const normalized = status.toUpperCase();
  if (['COMPLETE', 'PASS', 'VERIFIED', 'VERIFIED_FULL'].includes(normalized)) return <CheckCircle2 className="h-4 w-4" />;
  if (normalized === 'RUNNING') return <Activity className="h-4 w-4 animate-pulse" />;
  if (normalized === 'FAILED' || normalized === 'FAIL' || ['BLOCKED', 'NEEDS_REVIEW', 'REVIEW_REQUIRED', 'REQUIRED', 'REQUIRES_VERIFICATION'].includes(normalized)) {
    return <AlertTriangle className="h-4 w-4" />;
  }
  if (normalized === 'NOT_STARTED' || normalized === 'NOT_RUN' || normalized === 'WAITING') return <Clock3 className="h-4 w-4" />;
  return <CircleDashed className="h-4 w-4" />;
};

const formatMetric = (stage: ScanAssemblyStage) => {
  if (!stage.metrics.length) return 'No measured output yet';
  return stage.metrics
    .map((metric) => `${metric.value}${metric.total ? ` of ${metric.total}` : ''} ${metric.label}`)
    .join(' · ');
};

const measuredNumber = (stage: ScanAssemblyStage | undefined, labelFragment: string) => {
  const metric = stage?.metrics.find((candidate) => candidate.label.toLowerCase().includes(labelFragment.toLowerCase()));
  const value = Number(metric?.value);
  return Number.isFinite(value) ? value : 0;
};

const safeRecord = (value: unknown): Record<string, any> => value && typeof value === 'object' ? value as Record<string, any> : {};

const EvidenceCell: React.FC<{ label: string; value: string; status?: string }> = ({ label, value, status = 'UNKNOWN' }) => (
  <div className={`rounded-lg border px-3 py-2.5 ${statusTone(status)}`}>
    <p className="text-[11px] font-bold uppercase tracking-wide opacity-70">{label}</p>
    <p className="mt-1 text-sm font-bold break-words">{value}</p>
    <p className="mt-1 text-[10px] font-bold uppercase opacity-70">{status.replace(/_/g, ' ')}</p>
  </div>
);

const OrbAssemblyStatus: React.FC<{ assembly?: ScanAssemblyStatus | null; compact?: boolean }> = ({ assembly, compact = false }) => {
  const [crawlStats, setCrawlStats] = useState<Record<string, any> | null>(null);

  useEffect(() => {
    const match = window.location.pathname.match(/\/crawl\/(\d+)/i);
    if (!match) return;
    let cancelled = false;
    api.getCrawlJob(match[1])
      .then((crawl) => {
        if (!cancelled) setCrawlStats(safeRecord(crawl.stats));
      })
      .catch(() => {
        if (!cancelled) setCrawlStats(null);
      });
    return () => { cancelled = true; };
  }, [assembly?.crawl_job_id]);

  if (!assembly) return null;

  const pointerMapping = assembly.stages.find((stage) => stage.label === 'Pointer Mapping');
  const runtimeGuidance = assembly.stages.find((stage) => stage.label === 'Runtime Guidance');
  const pointerVerification = assembly.stages.find((stage) => stage.label === 'Pointer Verification');
  const pointerTargets = measuredNumber(pointerMapping, 'targets extracted');
  const guidanceTargets = measuredNumber(runtimeGuidance, 'guidance-eligible targets');
  const declaredReady = assembly.overall_status === 'orb_ready';
  const verificationComplete = pointerVerification?.status.toUpperCase() === 'COMPLETE';
  const runtimeReady = declaredReady
    && pointerMapping?.status.toUpperCase() === 'COMPLETE'
    && pointerTargets > 0
    && verificationComplete
    && runtimeGuidance?.status.toUpperCase() !== 'BLOCKED'
    && guidanceTargets > 0;
  const completedButNeedsReview = declaredReady && !runtimeReady;

  const intelligence = safeRecord(crawlStats?.site_intelligence);
  const platform = safeRecord(intelligence.platform);
  const builder = safeRecord(intelligence.site_builder);
  const assistant = safeRecord(intelligence.existing_conversational_interface);
  const browser = safeRecord(intelligence.browser_observation || crawlStats?.browser_observation);
  const google = safeRecord(intelligence.google_intelligence);
  const ga4 = safeRecord(google.ga4);
  const searchConsole = safeRecord(google.search_console);
  const assurance = safeRecord(intelligence.assurance);
  const urlDisposition = safeRecord(intelligence.url_disposition);
  const architecture = safeRecord(intelligence.content_architecture);
  const hasIntelligence = Object.keys(intelligence).length > 0;

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-[0.12em] text-brand-accent">ORB assembly status</p>
          <h2 className="mt-1 text-lg font-bold text-slate-950">
            {runtimeReady
              ? 'ORB knowledge base and verified guidance ready'
              : completedButNeedsReview
                ? 'Website scan completed — ORB verification remains'
                : assembly.overall_status === 'analysis_complete'
                  ? 'Website analysis complete; ORB verification stages remain'
                  : 'Website analysis running'}
          </h2>
          {(completedButNeedsReview || !verificationComplete) && (
            <p className="mt-1 max-w-3xl text-sm leading-6 text-amber-700">
              Crawl completion and high-confidence selectors are not verification. A target may guide only after independent browser verification and the final live-site rescan.
            </p>
          )}
        </div>
        <span className="rounded-full border border-slate-200 px-3 py-1 text-xs font-bold text-slate-600">
          {assembly.crawl_delay_seconds ? `${assembly.crawl_delay_seconds}s scan pause` : 'scan pause unset'}
        </span>
      </div>
      <div className={`mt-4 grid gap-2 ${compact ? 'md:grid-cols-2' : 'md:grid-cols-2 xl:grid-cols-3'}`}>
        {assembly.stages.map((stage) => (
          <div key={stage.id} className={`rounded-lg border px-3 py-2.5 ${statusTone(stage.status)}`}>
            <div className="flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2">
                <StatusIcon status={stage.status} />
                <h3 className="truncate text-sm font-bold">{stage.label}</h3>
              </div>
              <span className="shrink-0 text-[11px] font-bold uppercase">{stage.status.replace(/_/g, ' ')}</span>
            </div>
            <p className="mt-1 text-xs leading-5 text-slate-600">{formatMetric(stage)}</p>
            {stage.note && <p className="mt-1 text-xs leading-5 text-slate-500">{stage.note}</p>}
          </div>
        ))}
      </div>

      {hasIntelligence && (
        <div className="mt-5 border-t border-slate-200 pt-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-slate-700" />
                <h3 className="font-bold text-slate-950">Website Intelligence Assurance</h3>
              </div>
              <p className="mt-1 text-xs text-slate-500">Find broadly. Claim conservatively. Verify independently. Rescan before release.</p>
            </div>
            <span className={`rounded-full border px-3 py-1 text-xs font-bold ${statusTone(String(assurance.release_state || 'REQUIRES_VERIFICATION'))}`}>
              {String(assurance.release_state || 'REQUIRES_VERIFICATION').replace(/_/g, ' ')}
            </span>
          </div>
          <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            <EvidenceCell
              label="Platform"
              value={platform.platform || 'Not identified'}
              status={platform.evidence_state || 'UNKNOWN'}
            />
            <EvidenceCell
              label="Builder / Agency"
              value={builder.builder || 'Not identified'}
              status={builder.evidence_state || 'UNKNOWN'}
            />
            <EvidenceCell
              label="Existing Assistant"
              value={(assistant.providers || []).join(', ') || String(assistant.status || 'Unknown')}
              status={assistant.evidence_state || 'REQUIRES_VERIFICATION'}
            />
            <EvidenceCell
              label="Rendered Browser"
              value={`${browser.routes_observed || 0} / ${browser.routes_total || 0} routes observed`}
              status={browser.status || 'NOT_RUN'}
            />
            <EvidenceCell
              label="Google Analytics"
              value={ga4.status === 'retrieved' || ga4.status === 'RETRIEVED' ? 'Authenticated traffic retrieved' : 'Not connected / unavailable'}
              status={ga4.evidence_state || 'UNAVAILABLE'}
            />
            <EvidenceCell
              label="Search Console"
              value={searchConsole.status === 'RETRIEVED' ? 'Authenticated search data retrieved' : 'Not connected / unavailable'}
              status={searchConsole.evidence_state || 'UNAVAILABLE'}
            />
            <EvidenceCell
              label="URL Accounting"
              value={`${urlDisposition.unresolved_count || 0} unresolved discovered URLs`}
              status={urlDisposition.evidence_state || 'REQUIRES_VERIFICATION'}
            />
            <EvidenceCell
              label="Content Architecture"
              value={architecture.homepage_concentrated ? 'Homepage-dominant' : 'Distributed / not concentrated'}
              status="OBSERVED"
            />
          </div>
        </div>
      )}
    </section>
  );
};

export default OrbAssemblyStatus;
