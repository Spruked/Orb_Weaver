import React from 'react';
import { Activity, AlertTriangle, CheckCircle2, CircleDashed, Clock3 } from 'lucide-react';
import { ScanAssemblyStatus, ScanAssemblyStage } from '../services/api';

const statusTone = (status: string) => {
  if (status === 'complete') return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  if (status === 'running') return 'border-blue-200 bg-blue-50 text-blue-700';
  if (status === 'waiting') return 'border-slate-200 bg-slate-50 text-slate-600';
  if (status === 'needs_review' || status === 'required') return 'border-amber-200 bg-amber-50 text-amber-700';
  if (status === 'blocked') return 'border-red-200 bg-red-50 text-red-700';
  if (status === 'failed') return 'border-red-200 bg-red-50 text-red-700';
  return 'border-slate-200 bg-white text-slate-500';
};

const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
  if (status === 'complete') return <CheckCircle2 className="h-4 w-4" />;
  if (status === 'running') return <Activity className="h-4 w-4 animate-pulse" />;
  if (status === 'failed' || status === 'blocked' || status === 'required' || status === 'needs_review') return <AlertTriangle className="h-4 w-4" />;
  if (status === 'waiting') return <Clock3 className="h-4 w-4" />;
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

const OrbAssemblyStatus: React.FC<{ assembly?: ScanAssemblyStatus | null; compact?: boolean }> = ({ assembly, compact = false }) => {
  if (!assembly) return null;

  const pointerMapping = assembly.stages.find((stage) => stage.label === 'Pointer Mapping');
  const runtimeGuidance = assembly.stages.find((stage) => stage.label === 'Runtime Guidance');
  const pointerTargets = measuredNumber(pointerMapping, 'targets extracted');
  const guidanceTargets = measuredNumber(runtimeGuidance, 'guidance-eligible targets');
  const declaredReady = assembly.overall_status === 'orb_ready';
  const runtimeReady = declaredReady
    && pointerMapping?.status === 'complete'
    && pointerTargets > 0
    && runtimeGuidance?.status !== 'blocked'
    && guidanceTargets > 0;
  const completedButNeedsReview = declaredReady && !runtimeReady;

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
              : 'Website analysis running'}
          </h2>
          {completedButNeedsReview && (
            <p className="mt-1 max-w-3xl text-sm leading-6 text-amber-700">
              Crawl completion alone does not make the ORB ready. Pointable targets and guidance-eligible destinations must be measured before runtime guidance is enabled.
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
    </section>
  );
};

export default OrbAssemblyStatus;
