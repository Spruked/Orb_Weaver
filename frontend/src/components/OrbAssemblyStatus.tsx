import React, { useEffect, useState } from 'react';
import { Activity, AlertTriangle, CheckCircle2, CircleDashed, Clock3, ShieldCheck } from 'lucide-react';
import { ScanAssemblyStatus, ScanAssemblyStage } from '../services/api';

const statusTone = (status: string) => {
  const normalized = status.toUpperCase();
  if (normalized === 'COMPLETE' || normalized === 'READY') return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  if (normalized === 'RUNNING') return 'border-blue-200 bg-blue-50 text-blue-700';
  if (normalized === 'FAILED' || normalized === 'DEGRADED') return 'border-red-200 bg-red-50 text-red-700';
  if (['BLOCKED', 'NEEDS_REVIEW', 'REVIEW_REQUIRED', 'REQUIRED'].includes(normalized)) {
    return 'border-amber-200 bg-amber-50 text-amber-700';
  }
  return 'border-slate-200 bg-white text-slate-500';
};

const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
  const normalized = status.toUpperCase();
  if (normalized === 'COMPLETE' || normalized === 'READY') return <CheckCircle2 className="h-4 w-4" />;
  if (normalized === 'RUNNING') return <Activity className="h-4 w-4 animate-pulse" />;
  if (normalized === 'FAILED' || normalized === 'DEGRADED' || ['BLOCKED', 'NEEDS_REVIEW', 'REVIEW_REQUIRED', 'REQUIRED'].includes(normalized)) {
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

type AgencyStatus = {
  schema: 'tti.agency_status.v1';
  status: 'ready' | 'degraded';
  habitat: string;
  source_commit: string;
  registry_version?: string | null;
  registry_schema?: string | null;
  contract_present: boolean;
  primitives_present: boolean;
  primitive_counts: {
    motion: number;
    speech: number;
    expression: number;
  };
  active_orb_telemetry_connections: number;
  core4_authority: string;
  adapter_authority: string;
  errors: string[];
  checked_at: string;
};

const agencyStatusUrl = () => {
  const configured = process.env.REACT_APP_API_URL?.replace(/\/$/, '');
  if (configured) return `${configured}/ws/agency-status`;
  if (typeof window === 'undefined') return '/ws/agency-status';

  const { hostname, port, protocol } = window.location;
  const apiHostname = hostname === '0.0.0.0' ? '127.0.0.1' : hostname;
  const pairedApiPorts: Record<string, string> = {
    '16510': '16500',
    '16610': '16600',
    '16667': '19667',
    '16777': '16776',
  };
  const apiPort = pairedApiPorts[port];
  return apiPort ? `${protocol}//${apiHostname}:${apiPort}/ws/agency-status` : '/ws/agency-status';
};

const OrbAssemblyStatus: React.FC<{ assembly?: ScanAssemblyStatus | null; compact?: boolean }> = ({ assembly, compact = false }) => {
  const [agencyStatus, setAgencyStatus] = useState<AgencyStatus | null>(null);
  const [agencyError, setAgencyError] = useState('');

  useEffect(() => {
    let cancelled = false;

    const loadAgencyStatus = async () => {
      try {
        const response = await fetch(agencyStatusUrl(), { headers: { Accept: 'application/json' } });
        if (!response.ok) throw new Error(`Agency status HTTP ${response.status}`);
        const payload = await response.json() as AgencyStatus;
        if (!cancelled) {
          setAgencyStatus(payload);
          setAgencyError('');
        }
      } catch (error) {
        if (!cancelled) {
          setAgencyError(error instanceof Error ? error.message : 'Agency status unavailable');
        }
      }
    };

    loadAgencyStatus();
    const timer = window.setInterval(loadAgencyStatus, 10000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const agencyState = agencyStatus?.status || (agencyError ? 'degraded' : 'running');
  const agencyPanel = (
    <div className={`mt-4 rounded-lg border px-3 py-3 ${statusTone(agencyState)}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4" />
          <div>
            <p className="text-sm font-bold">Agency contract runtime</p>
            <p className="text-xs text-slate-600">
              {agencyStatus
                ? `${agencyStatus.registry_schema || 'registry unknown'} · v${agencyStatus.registry_version || 'unknown'} · ${agencyStatus.active_orb_telemetry_connections} live ORB telemetry connection${agencyStatus.active_orb_telemetry_connections === 1 ? '' : 's'}`
                : agencyError || 'Checking canonical contract and primitive registry…'}
            </p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1 text-[11px] font-bold uppercase">
          <StatusIcon status={agencyState} />
          {agencyState}
        </span>
      </div>
      {agencyStatus && (
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
          <span>Contract: {agencyStatus.contract_present ? 'present' : 'missing'}</span>
          <span>Registry: {agencyStatus.primitives_present ? 'present' : 'missing'}</span>
          <span>Motion: {agencyStatus.primitive_counts.motion}</span>
          <span>Speech: {agencyStatus.primitive_counts.speech}</span>
          <span>Expression: {agencyStatus.primitive_counts.expression}</span>
          <span>Core-4: existing Orb Weaver authority</span>
        </div>
      )}
      {agencyStatus?.errors?.length ? (
        <p className="mt-2 text-xs font-semibold text-red-700">{agencyStatus.errors.join(' · ')}</p>
      ) : null}
    </div>
  );

  if (!assembly) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <p className="text-xs font-extrabold uppercase tracking-[0.12em] text-brand-accent">ORB runtime status</p>
        <h2 className="mt-1 text-lg font-bold text-slate-950">Agency and telemetry monitor</h2>
        {agencyPanel}
      </section>
    );
  }

  const pointerMapping = assembly.stages.find((stage) => stage.label === 'Pointer Mapping');
  const runtimeGuidance = assembly.stages.find((stage) => stage.label === 'Runtime Guidance');
  const pointerTargets = measuredNumber(pointerMapping, 'targets extracted');
  const guidanceTargets = measuredNumber(runtimeGuidance, 'guidance-eligible targets');
  const declaredReady = assembly.overall_status === 'orb_ready';
  const runtimeReady = declaredReady
    && pointerMapping?.status.toUpperCase() === 'COMPLETE'
    && pointerTargets > 0
    && runtimeGuidance?.status.toUpperCase() !== 'BLOCKED'
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
                : assembly.overall_status === 'analysis_complete'
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
          {assembly.crawl_delay_seconds ? `${assembly.crawl_delay_seconds}s scan pause` : 'scan pause unset'}
        </span>
      </div>
      {agencyPanel}
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
