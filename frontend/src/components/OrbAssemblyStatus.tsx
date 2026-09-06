import React, { useEffect, useState } from 'react';
import { Activity, AlertTriangle, CheckCircle2, CircleDashed, Clock3 } from 'lucide-react';
import { api, CrawlJob, ScanAssemblyStatus, ScanAssemblyStage } from '../services/api';
import {
  ACTIVE_ORB_PROJECT_CONTEXT_EVENT,
  getActiveOrbProjectContext,
} from '../orb/activeProjectContext';

const statusTone = (status: string) => {
  const normalized = status.toUpperCase();
  if (normalized === 'COMPLETE') return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  if (normalized === 'RUNNING') return 'border-blue-200 bg-blue-50 text-blue-700';
  if (normalized === 'FAILED') return 'border-red-200 bg-red-50 text-red-700';
  if (['BLOCKED', 'NEEDS_REVIEW', 'REVIEW_REQUIRED', 'REQUIRED'].includes(normalized)) {
    return 'border-amber-200 bg-amber-50 text-amber-700';
  }
  return 'border-slate-200 bg-white text-slate-500';
};

const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
  const normalized = status.toUpperCase();
  if (normalized === 'COMPLETE') return <CheckCircle2 className="h-4 w-4" />;
  if (normalized === 'RUNNING') return <Activity className="h-4 w-4 animate-pulse" />;
  if (normalized === 'FAILED' || ['BLOCKED', 'NEEDS_REVIEW', 'REVIEW_REQUIRED', 'REQUIRED'].includes(normalized)) {
    return <AlertTriangle className="h-4 w-4" />;
  }
  if (normalized === 'NOT_STARTED' || normalized === 'WAITING') return <Clock3 className="h-4 w-4" />;
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

const asMetricRecord = (value: unknown): Record<string, number | boolean | string | null> | null => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  return value as Record<string, number | boolean | string | null>;
};

const OrbAssemblyStatus: React.FC<{ assembly?: ScanAssemblyStatus | null; compact?: boolean }> = ({ assembly, compact = false }) => {
  const [currentCrawl, setCurrentCrawl] = useState<CrawlJob | null>(null);

  useEffect(() => {
    let stopped = false;

    const refreshCurrentCrawl = async () => {
      const crawlId = getActiveOrbProjectContext()?.selected_crawl_job_id;
      if (!crawlId) {
        if (!stopped) setCurrentCrawl(null);
        return;
      }
      try {
        const crawl = await api.getCrawlJob(crawlId);
        if (!stopped) setCurrentCrawl(crawl);
      } catch {
        // The parent-provided assembly remains the fallback if current-scan lookup is unavailable.
      }
    };

    const handleProjectContext = () => { void refreshCurrentCrawl(); };
    void refreshCurrentCrawl();
    window.addEventListener(ACTIVE_ORB_PROJECT_CONTEXT_EVENT, handleProjectContext);
    const pollTimer = window.setInterval(() => { void refreshCurrentCrawl(); }, 4000);

    return () => {
      stopped = true;
      window.removeEventListener(ACTIVE_ORB_PROJECT_CONTEXT_EVENT, handleProjectContext);
      window.clearInterval(pollTimer);
    };
  }, []);

  const displayedAssembly = currentCrawl?.assembly_status || assembly || null;
  if (!displayedAssembly) return null;

  const pointerMapping = displayedAssembly.stages.find((stage) => stage.label === 'Pointer Mapping');
  const runtimeGuidance = displayedAssembly.stages.find((stage) => stage.label === 'Runtime Guidance');
  const pointerTargets = measuredNumber(pointerMapping, 'targets extracted');
  const guidanceTargets = measuredNumber(runtimeGuidance, 'guidance-eligible targets');
  const declaredReady = displayedAssembly.overall_status === 'orb_ready';
  const runtimeReady = declaredReady
    && pointerMapping?.status.toUpperCase() === 'COMPLETE'
    && pointerTargets > 0
    && runtimeGuidance?.status.toUpperCase() !== 'BLOCKED'
    && guidanceTargets > 0;
  const completedButNeedsReview = declaredReady && !runtimeReady;

  const lidarWeave = asMetricRecord(currentCrawl?.stats?.lidar_weave);
  const lidarCandidateCount = Number(lidarWeave?.pointer_candidate_count || 0);
  const lidarPersistentCount = Number(lidarWeave?.persistent_target_count || 0);
  const hasLidarEvidence = Boolean(lidarWeave);
  const isLegacyCompletedCrawl = Boolean(currentCrawl?.status === 'completed' && !hasLidarEvidence);
  const assemblyIsCurrentCrawl = Boolean(
    currentCrawl?.id && String(displayedAssembly.crawl_job_id) === String(currentCrawl.id)
  );
  const hasConfiguredScanPause = displayedAssembly.crawl_delay_seconds !== null
    && displayedAssembly.crawl_delay_seconds !== undefined;

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-[0.12em] text-brand-accent">ORB assembly status</p>
          <h2 className="mt-1 text-lg font-bold text-slate-950">
            {runtimeReady
              ? 'ORB knowledge base and guidance ready'
              : completedButNeedsReview
                ? 'Website scan completed — ORB assembly needs review'
                : displayedAssembly.overall_status === 'analysis_complete'
                  ? 'Website analysis complete; ORB stages remain'
                  : 'Website analysis running'}
          </h2>
          {completedButNeedsReview && (
            <p className="mt-1 max-w-3xl text-sm leading-6 text-amber-700">
              Crawl completion alone does not make the ORB ready. Pointable targets and guidance-eligible destinations must be measured before runtime guidance is enabled.
            </p>
          )}
        </div>
        <span className="rounded-full border border-slate-200 px-3 py-1 text-xs font-bold text-slate-600">
          {hasConfiguredScanPause ? `${displayedAssembly.crawl_delay_seconds}s scan pause` : 'scan pause unset'}
        </span>
      </div>

      {currentCrawl && (
        <div className="mt-4 rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-3 text-sm text-slate-700">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="font-bold text-slate-950">Current scan evidence · Crawl #{currentCrawl.id}</p>
              <p className="text-xs text-slate-600">
                Status: {currentCrawl.status} · {assemblyIsCurrentCrawl ? 'assembly shown from this crawl' : 'current crawl loaded separately from completed audit evidence'}
              </p>
            </div>
            <span className="rounded-full border border-cyan-200 bg-white px-2.5 py-1 text-xs font-bold text-cyan-800">
              LiDAR 2D Mapping
            </span>
          </div>
          {hasLidarEvidence ? (
            <div className="mt-2 grid gap-2 sm:grid-cols-3">
              <div className="rounded bg-white px-2.5 py-2">
                <p className="text-lg font-bold text-slate-950">{lidarCandidateCount}</p>
                <p className="text-xs text-slate-500">scan-discovered targets</p>
              </div>
              <div className="rounded bg-white px-2.5 py-2">
                <p className="text-lg font-bold text-slate-950">{lidarPersistentCount}</p>
                <p className="text-xs text-slate-500">persistent target identities</p>
              </div>
              <div className="rounded bg-white px-2.5 py-2">
                <p className="text-sm font-bold text-slate-950">Runtime verification required</p>
                <p className="text-xs text-slate-500">live geometry is not fabricated by the crawler</p>
              </div>
            </div>
          ) : isLegacyCompletedCrawl ? (
            <p className="mt-2 font-semibold text-amber-800">Legacy crawl — LiDAR evidence was not recorded for this crawl.</p>
          ) : (
            <p className="mt-2 font-semibold text-slate-700">LiDAR evidence has not been recorded yet for this in-progress crawl.</p>
          )}
        </div>
      )}

      <div className={`mt-4 grid gap-2 ${compact ? 'md:grid-cols-2' : 'md:grid-cols-2 xl:grid-cols-3'}`}>
        {displayedAssembly.stages.map((stage) => (
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
    </section>
  );
};

export default OrbAssemblyStatus;
