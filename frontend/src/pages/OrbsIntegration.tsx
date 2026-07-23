import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Activity, AlertTriangle, ArrowLeft, ArrowRight, CheckCircle2, CircleDashed, LockKeyhole, ShieldCheck, SlidersHorizontal } from 'lucide-react';
import { api, OrbsAllowedAction, OrbsStageSnapshot } from '../services/api';

const JOURNEY = [
  ['preflight', 'Preflight'],
  ['crawl', 'Crawl'],
  ['final_audit', 'Final Audit'],
  ['orbs', 'ORBS'],
  ['package_presentation_and_recommendation', 'Package Presentation and Recommendation'],
  ['final_closer_questionnaire', 'Final Closer Questionnaire'],
  ['package_selection_commitment', 'Package Selection / Commitment'],
  ['build_configuration', 'Build Configuration'],
  ['final_order_review', 'Final Order Review'],
  ['signature', 'Signature'],
  ['checkout', 'Checkout'],
  ['verified_payment', 'Verified Payment'],
  ['fulfillment', 'Fulfillment'],
  ['review_required', 'Review Required'],
  ['package_generation', 'Package Generation'],
  ['installation', 'Installation'],
  ['launch_verification', 'Launch Verification'],
  ['live', 'Live']
] as const;

const FIELD_LABELS: Record<string, string> = {
  business_outcome: 'Business outcome that matters most',
  remaining_concern: 'Remaining concern or uncertainty',
  timing: 'Expected timing',
  support_expectation: 'Support expectation',
  readiness: 'Readiness to proceed',
  marketplace_product_id: 'Approved package',
  priority_routes: 'Priority visitor routes (one per line)',
  installation_method: 'Installation method',
  support_level: 'Support level',
  launch_timing: 'Launch timing',
  technical_choices: 'Other technical build choices',
  signer_name: 'Signer name',
  accepted_terms: 'Accept the displayed order and terms',
  signature_hash: 'Signature reference',
  provider: 'Payment provider',
  method: 'Installation method',
  evidence: 'Installation evidence',
  installed_at: 'Installation date/time',
  verification_evidence: 'Launch verification evidence',
  verified_url: 'Verified live URL',
  verified_at: 'Verification date/time'
};

function humanize(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

const OrbsIntegration: React.FC = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [snapshot, setSnapshot] = useState<OrbsStageSnapshot | null>(null);
  const [inputs, setInputs] = useState<Record<string, string | boolean>>({});
  const [loading, setLoading] = useState(true);
  const [workingAction, setWorkingAction] = useState('');
  const [error, setError] = useState('');

  const load = async () => {
    if (!projectId) return;
    setLoading(true);
    setError('');
    try {
      setSnapshot(await api.getOrbsStage(projectId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load the authoritative ORBS stage');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, [projectId]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { setInputs({}); }, [snapshot?.snapshot_version, snapshot?.current_stage]);

  const packages = useMemo(() => {
    const value = snapshot?.approved_stage_evidence?.approved_packages;
    return Array.isArray(value) ? value as Array<Record<string, unknown>> : [];
  }, [snapshot]);

  const submit = async (action: OrbsAllowedAction) => {
    if (!snapshot || !projectId) return;
    if (action.confirmation_required && !window.confirm(`Confirm: ${action.display_label} for ${snapshot.project_display_name}?`)) return;
    const actionInputs: Record<string, unknown> = {};
    for (const field of action.allowed_input_fields) {
      const value = inputs[field];
      if (field === 'priority_routes') actionInputs[field] = String(value || '').split('\n').map((item) => item.trim()).filter(Boolean);
      else if (field === 'accepted_terms') actionInputs[field] = value === true;
      else if (field === 'technical_choices') actionInputs[field] = value ? { notes: String(value) } : {};
      else actionInputs[field] = value ?? '';
    }
    const idempotencyKey = window.crypto?.randomUUID?.() || `${snapshot.project_id}-${action.name}-${snapshot.snapshot_version}-${Date.now()}`;
    setWorkingAction(action.name);
    setError('');
    try {
      const fresh = await api.submitOrbsStageAction(projectId, {
        project_id: snapshot.project_id,
        build_order_id: snapshot.build_order_id,
        action: action.name,
        expected_stage: snapshot.current_stage,
        snapshot_version: snapshot.snapshot_version,
        inputs: actionInputs,
        ...(action.confirmation_required ? { confirmation_evidence: {
          confirmed: true,
          project_id: snapshot.project_id,
          action_name: action.name,
          snapshot_version: snapshot.snapshot_version,
          confirmed_at: new Date().toISOString(),
          method: 'explicit_browser_confirmation',
          statement_hash: idempotencyKey
        }} : {})
      }, idempotencyKey);
      setSnapshot(fresh);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The Stage Governor rejected this action');
      await load();
    } finally {
      setWorkingAction('');
    }
  };

  if (loading && !snapshot) return <div className="card text-slate-500">Loading the authoritative ORBS journey…</div>;
  if (!snapshot) return <div className="card border-red-200 bg-red-50 text-red-700">{error || 'Project stage unavailable.'}</div>;

  const technicalGate = ['preflight', 'crawl', 'final_audit'].includes(snapshot.current_stage);
  const currentIndex = JOURNEY.findIndex(([key]) => key === snapshot.current_stage);

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="bg-slate-950 px-6 py-7 text-white md:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <button onClick={() => navigate(`/dashboard?project=${encodeURIComponent(snapshot.project_id)}`)} className="inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white">
              <ArrowLeft className="h-4 w-4" /> Back to technical results
            </button>
            <button onClick={() => navigate(`/orbs/${snapshot.project_id}/dock`)} className="inline-flex items-center gap-2 rounded-md border border-cyan-300/50 px-4 py-2 text-sm font-bold text-cyan-100 hover:bg-white/10">
              <SlidersHorizontal className="h-4 w-4" /> Dock Station
            </button>
          </div>
          <p className="mt-5 text-xs font-bold uppercase tracking-[0.16em] text-cyan-300">Project-bound supported integration</p>
          <h1 className="mt-2 text-3xl font-bold md:text-4xl">ORBS — Origin of Reasoning Bilateral Substrate</h1>
          <p className="mt-3 text-lg text-slate-200">Review and support for Website {snapshot.project_display_name} integration.</p>
          <div className="mt-5 flex flex-wrap gap-2 text-xs font-semibold text-slate-300">
            <span className="rounded-full border border-white/20 px-3 py-1">Project #{snapshot.project_id}</span>
            <span className="rounded-full border border-white/20 px-3 py-1">Stage: {humanize(snapshot.current_stage)}</span>
            <span className="rounded-full border border-white/20 px-3 py-1">Status: {humanize(snapshot.stage_status)}</span>
          </div>
        </div>
        <div className="overflow-x-auto border-t border-slate-800 bg-slate-900 px-5 py-4">
          <ol className="flex min-w-max items-center gap-2" aria-label="Authoritative customer journey">
            {JOURNEY.map(([key, label], index) => {
              const complete = snapshot.completed_stages.includes(key);
              const current = key === snapshot.current_stage;
              return <React.Fragment key={key}><li className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold ${current ? 'bg-brand-orange text-brand-dark' : complete ? 'bg-emerald-900 text-emerald-200' : 'bg-white/10 text-slate-300'}`}>{complete ? <CheckCircle2 className="h-3.5 w-3.5" /> : <CircleDashed className="h-3.5 w-3.5" />}{label}</li>{index < JOURNEY.length - 1 && <ArrowRight className="h-3.5 w-3.5 text-slate-600" />}</React.Fragment>;
            })}
          </ol>
        </div>
      </section>

      {error && <div className="card border-red-200 bg-red-50 text-sm font-semibold text-red-700">{error}</div>}

      {technicalGate && (
        <section className="card border-amber-200 bg-amber-50">
          <div className="flex items-start gap-3"><LockKeyhole className="mt-0.5 h-6 w-6 text-amber-700" /><div><h2 className="text-xl font-bold text-slate-950">ORBS assessment is locked</h2><p className="mt-1 text-sm text-slate-700">Package presentation and purchase remain unavailable until Preflight, Crawl, and Final Audit are separately complete for this project.</p></div></div>
        </section>
      )}

      {snapshot.blocking_reason && <section className="card border-amber-200 bg-amber-50"><div className="flex gap-3"><AlertTriangle className="h-5 w-5 text-amber-700" /><div><h2 className="font-bold text-slate-950">Current blocker</h2><p className="mt-1 text-sm text-slate-700">{snapshot.blocking_reason}</p></div></div></section>}

      <section className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="card">
          <div className="flex items-center gap-3"><ShieldCheck className="h-5 w-5 text-brand-accent" /><h2 className="text-xl font-bold text-slate-950">Approved stage evidence</h2></div>
          <p className="mt-2 text-sm text-slate-600">This is the project-scoped evidence the governor permits at the current stage. It contains no provider secrets or unrestricted handlers.</p>
          <pre className="mt-4 max-h-[34rem] overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-200">{JSON.stringify(snapshot.approved_stage_evidence, null, 2)}</pre>
        </div>
        <div className="space-y-5">
          <div className="card">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Customer action</p>
            <h2 className="mt-2 text-xl font-bold text-slate-950">{snapshot.customer_action_required || (snapshot.stage_status === 'in_progress' ? 'Wait for the current operation' : 'No action required')}</h2>
            {snapshot.stage_status === 'in_progress' && <p className="mt-2 text-sm text-slate-600">The authoritative operation is running. Refresh to retrieve its current state.</p>}
            <button onClick={() => void load()} className="mt-4 rounded-lg border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50">Refresh stage</button>
          </div>

          {snapshot.allowed_actions.map((action) => (
            <div key={action.name} className="card border-cyan-200">
              <h3 className="text-lg font-bold text-slate-950">{action.display_label}</h3>
              {action.reason_available && <p className="mt-1 text-sm text-slate-600">{action.reason_available}</p>}
              {action.allowed_input_fields.length > 0 && <div className="mt-4 space-y-3">
                {action.allowed_input_fields.map((field) => (
                  <label key={field} className="block text-sm font-bold text-slate-800">
                    {FIELD_LABELS[field] || humanize(field)}
                    {field === 'marketplace_product_id' ? (
                      <select value={String(inputs[field] || '')} onChange={(event) => setInputs((current) => ({ ...current, [field]: event.target.value }))} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-normal">
                        <option value="">Select an approved package</option>
                        {packages.map((item) => <option key={String(item.marketplace_product_id)} value={String(item.marketplace_product_id)}>{String(item.name)} · {String(item.tier || '')} · {String(item.price_cents)} {String(item.currency).toUpperCase()}</option>)}
                      </select>
                    ) : field === 'provider' ? (
                      <select value={String(inputs[field] || '')} onChange={(event) => setInputs((current) => ({ ...current, [field]: event.target.value }))} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-normal"><option value="">Select provider</option><option value="stripe">Stripe · verified webhook</option></select>
                    ) : field === 'accepted_terms' ? (
                      <input type="checkbox" checked={inputs[field] === true} onChange={(event) => setInputs((current) => ({ ...current, [field]: event.target.checked }))} className="ml-3" />
                    ) : (
                      <textarea value={String(inputs[field] || '')} onChange={(event) => setInputs((current) => ({ ...current, [field]: event.target.value }))} rows={field === 'priority_routes' ? 4 : 2} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" />
                    )}
                  </label>
                ))}
              </div>}
              <button onClick={() => void submit(action)} disabled={Boolean(workingAction)} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand-orange px-4 py-3 font-bold text-brand-dark hover:bg-brand-accent hover:text-white disabled:opacity-50">
                {workingAction === action.name && <Activity className="h-4 w-4 animate-pulse" />}{action.display_label}{action.confirmation_required && ' · Confirmation required'}
              </button>
            </div>
          ))}
        </div>
      </section>

      <p className="text-center text-xs text-slate-500">Authoritative stage {Math.max(currentIndex + 1, 1)} of {JOURNEY.length} · Snapshot {snapshot.snapshot_version} · Updated {new Date(snapshot.updated_at).toLocaleString()}</p>
    </div>
  );
};

export default OrbsIntegration;
