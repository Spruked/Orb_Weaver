import React from 'react';
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { AuditDelta } from '../services/api';

const labelFor = (key: string) => key.startsWith('score_')
  ? `${key.replace('score_', '').replace(/_/g, ' ')} score`
  : key.replace(/_/g, ' ');

const toneFor = (key: string, value: number) => {
  if (value === 0) return 'text-slate-600';
  const isScore = key.startsWith('score_');
  const isIssue = key.includes('issue') || key.includes('critical') || key.includes('warning');
  if ((isScore && value > 0) || (isIssue && value < 0)) return 'text-emerald-700';
  if ((isScore && value < 0) || (isIssue && value > 0)) return 'text-red-700';
  return 'text-blue-700';
};

const ChangeIcon: React.FC<{ value: number }> = ({ value }) => {
  if (value > 0) return <ArrowUpRight className="h-4 w-4" />;
  if (value < 0) return <ArrowDownRight className="h-4 w-4" />;
  return <Minus className="h-4 w-4" />;
};

const AuditChangeSummary: React.FC<{ delta?: AuditDelta | null }> = ({ delta }) => {
  const entries = Object.entries(delta?.deltas || {}).filter(([, value]) => Number.isFinite(Number(value)));

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-[0.12em] text-brand-accent">Re-audit differences</p>
          <h2 className="mt-1 text-lg font-bold text-slate-950">What changed since the previous audit</h2>
        </div>
        {delta?.latest_audit_id && <span className="rounded-full border border-slate-200 px-3 py-1 text-xs font-bold text-slate-600">Audit #{delta.latest_audit_id}</span>}
      </div>
      {!delta ? (
        <p className="mt-3 text-sm text-slate-500">No audit has been recorded for this workspace yet.</p>
      ) : !delta.has_previous ? (
        <p className="mt-3 text-sm text-slate-500">This is the first audit for the project, so there is no previous report to compare.</p>
      ) : entries.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">No measured audit differences were found.</p>
      ) : (
        <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {entries.map(([key, raw]) => {
            const value = Number(raw);
            return (
              <div key={key} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
                <div className={`flex items-center justify-between gap-3 font-bold ${toneFor(key, value)}`}>
                  <span className="text-sm capitalize text-slate-800">{labelFor(key)}</span>
                  <span className="inline-flex items-center gap-1 text-sm">
                    <ChangeIcon value={value} />
                    {value > 0 ? '+' : ''}{value.toFixed(0)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};

export default AuditChangeSummary;
