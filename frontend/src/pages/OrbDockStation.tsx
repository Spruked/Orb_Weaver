import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  BrainCircuit,
  CheckCircle2,
  Download,
  FileCheck2,
  Loader2,
  LockKeyhole,
  Palette,
  Plus,
  Save,
  ShieldCheck,
  SlidersHorizontal,
  Target,
  Trash2,
  Volume2,
} from 'lucide-react';
import {
  api,
  DockAdditionalGuideRail,
  DockBusinessObjective,
  DockConfiguration,
  DockOllamaStatus,
  DockSituationalGuideRail,
  OrbDockStation,
} from '../services/api';
import OrbAssemblyStatus from '../components/OrbAssemblyStatus';

type TabId = 'doctrine' | 'behavior' | 'appearance' | 'models' | 'objectives' | 'additional' | 'situational';

const TABS: Array<{ id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }> = [
  { id: 'doctrine', label: 'Locked Doctrine', icon: ShieldCheck },
  { id: 'behavior', label: 'Behavior', icon: Volume2 },
  { id: 'appearance', label: 'ORB Skins', icon: Palette },
  { id: 'models', label: 'Models', icon: BrainCircuit },
  { id: 'objectives', label: 'Business Objectives', icon: Target },
  { id: 'additional', label: 'Additional Guide Rails', icon: SlidersHorizontal },
  { id: 'situational', label: 'Situational Guide Rails', icon: FileCheck2 },
];

const inputClass = 'mt-1.5 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-brand-accent focus:outline-none focus:ring-2 focus:ring-brand-orange/20';
const labelClass = 'block text-sm font-bold text-slate-800';
const providerDefaults: Record<DockConfiguration['llm']['provider'], Partial<DockConfiguration['llm']>> = {
  runtime_default: { model: null, base_url: null, api_key_env: null },
  ollama_local: { model: null, base_url: null, api_key_env: null },
  openai_api: { model: 'gpt-4.1-mini', base_url: null, api_key_env: 'OPENAI_API_KEY' },
  anthropic_api: { model: 'claude-3-5-sonnet-latest', base_url: null, api_key_env: 'ANTHROPIC_API_KEY' },
  google_api: { model: 'gemini-2.5-flash', base_url: null, api_key_env: 'GEMINI_API_KEY' },
  openai_compatible: { model: '', base_url: 'http://127.0.0.1:11434/v1', api_key_env: null },
};

const lines = (value: string) => value.split('\n').map((item) => item.trim()).filter(Boolean);
const lineText = (value: string[] | undefined) => (value || []).join('\n');
const makeId = (prefix: string) => `${prefix}_${Date.now().toString(36)}`;

const blankObjective = (): DockBusinessObjective => ({
  objective_id: makeId('objective'),
  name: '',
  enabled: true,
  completion_evidence: [],
  required_fields: [],
  permitted_routes: [],
  permitted_tools: [],
  escalation_route: '',
  success_condition: '',
  failure_condition: '',
});

const blankAdditionalRail = (): DockAdditionalGuideRail => ({
  guide_rail_id: makeId('rail'),
  name: '',
  enabled: true,
  applies_when: '',
  orb_should: '',
  orb_must_not: '',
  permitted_actions: [],
  required_evidence: [],
  escalate_when: '',
  priority: 'medium',
  effective_from: null,
  effective_until: null,
  owner_note: '',
});

const blankSituationalRail = (): DockSituationalGuideRail => ({
  guide_rail_id: makeId('situation'),
  name: '',
  enabled: true,
  conditions: {
    current_pages: [],
    visitor_types: [],
    workflow_stages: [],
    product_categories: [],
    business_hours: [],
    geographic_eligibility: [],
    minimum_confidence: null,
    authentication_states: [],
    active_promotions: [],
    prior_history_terms: [],
  },
  orb_should: '',
  orb_must_not: '',
  permitted_actions: [],
  required_evidence: [],
  escalate_when: '',
  priority: 'medium',
  owner_note: '',
});

const TextAreaField: React.FC<{
  label: string;
  value: string;
  onChange: (value: string) => void;
  rows?: number;
  hint?: string;
  placeholder?: string;
}> = ({ label, value, onChange, rows = 3, hint, placeholder }) => (
  <label className={labelClass}>
    {label}
    {hint && <span className="ml-1 font-normal text-slate-500">{hint}</span>}
    <textarea className={inputClass} rows={rows} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
  </label>
);

const ListField: React.FC<{
  label: string;
  value: string[];
  onChange: (value: string[]) => void;
  hint?: string;
  placeholder?: string;
}> = ({ label, value, onChange, hint = '(one per line)', placeholder }) => (
  <TextAreaField label={label} hint={hint} rows={3} value={lineText(value)} placeholder={placeholder} onChange={(next) => onChange(lines(next))} />
);

const Toggle: React.FC<{ checked: boolean; onChange: (checked: boolean) => void; label: string }> = ({ checked, onChange, label }) => (
  <label className="inline-flex cursor-pointer items-center gap-2 text-sm font-bold text-slate-700">
    <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-4 w-4 rounded border-slate-300 text-brand-accent focus:ring-brand-orange" />
    {label}
  </label>
);

const PriorityField: React.FC<{ value: DockAdditionalGuideRail['priority']; onChange: (value: DockAdditionalGuideRail['priority']) => void }> = ({ value, onChange }) => (
  <label className={labelClass}>Priority
    <select className={inputClass} value={value} onChange={(event) => onChange(event.target.value as DockAdditionalGuideRail['priority'])}>
      <option value="low">Low</option>
      <option value="medium">Medium</option>
      <option value="high">High</option>
      <option value="critical">Critical</option>
    </select>
  </label>
);

const OrbDockStationPage: React.FC = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [dock, setDock] = useState<OrbDockStation | null>(null);
  const [draft, setDraft] = useState<DockConfiguration | null>(null);
  const [tab, setTab] = useState<TabId>('doctrine');
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState('');
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [ollama, setOllama] = useState<DockOllamaStatus | null>(null);
  const [pullModel, setPullModel] = useState('');

  const load = async () => {
    if (!projectId) return;
    setLoading(true);
    setError('');
    try {
      const response = await api.getOrbDock(projectId);
      setDock(response);
      setDraft(response.configuration);
      setDirty(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load the Dock Station');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, [projectId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (tab !== 'models' || !projectId || ollama) return;
    void api.getOrbDockOllama(projectId).then(setOllama).catch((err) => setError(err instanceof Error ? err.message : 'Unable to inspect Ollama'));
  }, [tab, projectId, ollama]);

  const updateDraft = (updater: (current: DockConfiguration) => DockConfiguration) => {
    setDraft((current) => current ? updater(current) : current);
    setDirty(true);
    setNotice('');
  };

  const save = async (quiet = false) => {
    if (!projectId || !draft) return null;
    setWorking('save');
    setError('');
    try {
      const response = await api.saveOrbDock(projectId, draft);
      setDock(response);
      setDraft(response.configuration);
      setDirty(false);
      if (!quiet) setNotice('Draft saved.');
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save the Dock Station draft');
      return null;
    } finally {
      setWorking('');
    }
  };

  const compile = async () => {
    if (!projectId) return;
    if (dirty && !await save(true)) return;
    setWorking('compile');
    setError('');
    try {
      const response = await api.compileOrbDock(projectId);
      setDock(response);
      setNotice(response.compile.publishable ? 'Policy compiled and is ready to publish.' : 'Compilation found items that must be resolved.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to compile the Dock policy');
    } finally {
      setWorking('');
    }
  };

  const publish = async () => {
    if (!projectId) return;
    if (dirty && !await save(true)) return;
    setWorking('publish');
    setError('');
    try {
      const response = await api.publishOrbDock(projectId);
      setDock(response);
      setDraft(response.configuration);
      setNotice(`Published policy version ${response.publication.version}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The Dock policy could not be published');
    } finally {
      setWorking('');
    }
  };

  const pull = async () => {
    if (!projectId || !pullModel.trim()) return;
    setWorking('pull');
    setError('');
    try {
      await api.pullOrbDockOllamaModel(projectId, pullModel.trim());
      const status = await api.getOrbDockOllama(projectId);
      setOllama(status);
      updateDraft((current) => ({ ...current, llm: { ...current.llm, provider: 'ollama_local', model: pullModel.trim() } }));
      setNotice(`${pullModel.trim()} is available in local Ollama.`);
      setPullModel('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to download the Ollama model');
    } finally {
      setWorking('');
    }
  };

  const compileCount = (dock?.compile.blockers.length || 0) + (dock?.compile.warnings.length || 0);
  const selectedSkin = useMemo(() => dock?.skins.find((skin) => skin.skin_id === draft?.appearance.skin_id), [dock, draft]);

  if (loading && !dock) return <div className="rounded-md border border-slate-200 bg-white p-8 text-slate-500">Loading Dock Station...</div>;
  if (!dock || !draft) return <div className="rounded-md border border-red-200 bg-red-50 p-5 text-red-700">{error || 'Dock Station unavailable.'}</div>;

  const updateObjective = (index: number, patch: Partial<DockBusinessObjective>) => updateDraft((current) => ({
    ...current,
    business_objectives: current.business_objectives.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item),
  }));
  const updateAdditional = (index: number, patch: Partial<DockAdditionalGuideRail>) => updateDraft((current) => ({
    ...current,
    additional_guide_rails: current.additional_guide_rails.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item),
  }));
  const updateSituational = (index: number, patch: Partial<DockSituationalGuideRail>) => updateDraft((current) => ({
    ...current,
    situational_guide_rails: current.situational_guide_rails.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item),
  }));
  const updateBehavior = (patch: Partial<DockConfiguration['behavior']>) => updateDraft((current) => ({
    ...current,
    behavior: { ...current.behavior, ...patch },
  }));
  const updateLlm = (patch: Partial<DockConfiguration['llm']>) => updateDraft((current) => ({
    ...current,
    llm: { ...current.llm, ...patch },
  }));
  const selectProvider = (provider: DockConfiguration['llm']['provider']) => updateDraft((current) => ({
    ...current,
    llm: {
      ...current.llm,
      ...providerDefaults[provider],
      provider,
    },
  }));

  return (
    <div className="space-y-5">
      <header className="border-b border-slate-300 pb-5">
        <button onClick={() => navigate(`/orbs/${dock.project.id}`)} className="inline-flex items-center gap-2 text-sm font-bold text-brand-accent hover:text-brand-dark">
          <ArrowLeft className="h-4 w-4" /> ORBS integration
        </button>
        <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-extrabold uppercase tracking-[0.14em] text-brand-accent">Website ORB control surface</p>
            <h1 className="mt-1 text-3xl font-extrabold text-slate-950">Dock Station</h1>
            <p className="mt-2 text-sm text-slate-600">{dock.project.name} · {dock.project.domain}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => void save()} disabled={!dirty || Boolean(working)} className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-45">
              {working === 'save' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save draft
            </button>
            <button onClick={() => void compile()} disabled={Boolean(working)} className="inline-flex items-center gap-2 rounded-md border border-brand-accent px-4 py-2.5 text-sm font-bold text-brand-accent hover:bg-cyan-50 disabled:opacity-45">
              {working === 'compile' ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileCheck2 className="h-4 w-4" />} Compile
            </button>
            <button onClick={() => void publish()} disabled={Boolean(working) || !dock.compile.publishable} className="inline-flex items-center gap-2 rounded-md bg-brand-orange px-4 py-2.5 text-sm font-bold text-brand-dark hover:bg-brand-accent hover:text-white disabled:opacity-45">
              {working === 'publish' ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />} Publish
            </button>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs font-bold text-slate-600">
          <span>Status: {dirty ? 'Unsaved draft' : dock.publication.status}</span>
          <span>Published version: {dock.publication.version}</span>
          <span className={dock.compile.publishable ? 'text-emerald-700' : 'text-amber-700'}>
            {dock.compile.publishable ? 'Compile ready' : `${dock.compile.blockers.length} blocker${dock.compile.blockers.length === 1 ? '' : 's'}`}
          </span>
        </div>
      </header>

      {error && <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</div>}
      {notice && <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800">{notice}</div>}
      <OrbAssemblyStatus assembly={dock.latest_crawl?.assembly_status} compact />
      {compileCount > 0 && (
        <section className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" />
            <div className="min-w-0">
              <h2 className="font-bold text-slate-950">Compiler findings</h2>
              {[...dock.compile.blockers, ...dock.compile.warnings].map((issue, index) => (
                <p key={`${issue.path}-${index}`} className="mt-1 text-sm text-slate-700"><strong>{issue.path}:</strong> {issue.message}</p>
              ))}
            </div>
          </div>
        </section>
      )}

      <div className="overflow-x-auto border-b border-slate-300">
        <nav className="flex min-w-max gap-1" aria-label="Dock Station sections">
          {TABS.map((item) => {
            const Icon = item.icon;
            return (
              <button key={item.id} onClick={() => setTab(item.id)} className={`inline-flex items-center gap-2 border-b-2 px-3 py-3 text-sm font-bold ${tab === item.id ? 'border-brand-orange text-brand-dark' : 'border-transparent text-slate-500 hover:text-slate-900'}`}>
                <Icon className="h-4 w-4" /> {item.label}
              </button>
            );
          })}
        </nav>
      </div>

      {tab === 'doctrine' && (
        <section>
          <div className="max-w-3xl">
            <h2 className="text-2xl font-bold text-slate-950">Locked ORB doctrine</h2>
            <p className="mt-2 text-sm text-slate-600">These runtime protections are owned by Orb Weaver and cannot be changed in a customer policy.</p>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {dock.locked_doctrine.rules.map((rule) => (
              <div key={rule.id} className="rounded-md border border-slate-200 bg-white p-4">
                <div className="flex items-start gap-3"><LockKeyhole className="mt-0.5 h-5 w-5 text-brand-accent" /><div><h3 className="font-bold text-slate-950">{rule.label}</h3><p className="mt-1 text-sm leading-6 text-slate-600">{rule.rule}</p></div></div>
              </div>
            ))}
          </div>
        </section>
      )}

      {tab === 'behavior' && (
        <section className="max-w-5xl">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-2xl font-bold text-slate-950">ORB behavior</h2>
              <p className="mt-2 text-sm text-slate-600">Set the spoken personality, greeting, and voice startup posture that publish with this ORB.</p>
            </div>
          </div>
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <div className="rounded-md border border-slate-200 bg-white p-5">
              <h3 className="font-bold text-slate-950">Voice posture</h3>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <label className={labelClass}>Tone
                  <select className={inputClass} value={draft.behavior.tone} onChange={(event) => updateBehavior({ tone: event.target.value as DockConfiguration['behavior']['tone'] })}>
                    <option value="warm">Warm</option>
                    <option value="calm">Calm</option>
                    <option value="professional">Professional</option>
                    <option value="playful">Playful</option>
                    <option value="direct">Direct</option>
                  </select>
                </label>
                <label className={labelClass}>Response style
                  <select className={inputClass} value={draft.behavior.response_style} onChange={(event) => updateBehavior({ response_style: event.target.value as DockConfiguration['behavior']['response_style'] })}>
                    <option value="concise">Concise</option>
                    <option value="guided">Guided</option>
                    <option value="diagnostic">Diagnostic</option>
                    <option value="sales_assistant">Sales assistant</option>
                  </select>
                </label>
              </div>
              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                <Toggle checked={draft.behavior.greeting_enabled} onChange={(greeting_enabled) => updateBehavior({ greeting_enabled })} label="Startup greeting" />
                <Toggle checked={draft.behavior.startup_listening_enabled} onChange={(startup_listening_enabled) => updateBehavior({ startup_listening_enabled })} label="Auto listening" />
                <Toggle checked={draft.behavior.voice_only} onChange={(voice_only) => updateBehavior({ voice_only })} label="Voice only" />
                <Toggle checked={draft.behavior.mute_by_default} onChange={(mute_by_default) => updateBehavior({ mute_by_default })} label="Mute by default" />
                <Toggle checked={draft.behavior.sleep_by_default} onChange={(sleep_by_default) => updateBehavior({ sleep_by_default })} label="Sleep by default" />
              </div>
            </div>
            <div className="rounded-md border border-slate-200 bg-white p-5">
              <h3 className="font-bold text-slate-950">Job and rules</h3>
              <div className="mt-4 space-y-4">
                <TextAreaField label="Greeting script" value={draft.behavior.greeting_script} onChange={(greeting_script) => updateBehavior({ greeting_script })} rows={4} />
                <TextAreaField label="Job description" value={draft.behavior.job_description} onChange={(job_description) => updateBehavior({ job_description })} rows={5} />
                <TextAreaField label="Persona notes" value={draft.behavior.persona_notes} onChange={(persona_notes) => updateBehavior({ persona_notes })} rows={5} />
                <ListField label="Must follow rules" value={draft.behavior.must_follow_rules} onChange={(must_follow_rules) => updateBehavior({ must_follow_rules })} />
                <ListField label="Must not rules" value={draft.behavior.must_not_rules} onChange={(must_not_rules) => updateBehavior({ must_not_rules })} />
                <ListField label="Prohibited tone" value={draft.behavior.prohibited_tone} onChange={(prohibited_tone) => updateBehavior({ prohibited_tone })} />
              </div>
            </div>
          </div>
        </section>
      )}

      {tab === 'appearance' && (
        <section>
          <h2 className="text-2xl font-bold text-slate-950">ORB skins</h2>
          <p className="mt-2 text-sm text-slate-600">Choose the deployed Website ORB body. Factory Default remains available as a verified fallback.</p>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {dock.skins.map((skin) => {
              const selected = skin.skin_id === draft.appearance.skin_id;
              return (
                <button key={skin.skin_id} onClick={() => updateDraft((current) => ({ ...current, appearance: { skin_id: skin.skin_id } }))} className={`rounded-md border bg-white p-3 text-left ${selected ? 'border-brand-orange ring-2 ring-brand-orange/25' : 'border-slate-200 hover:border-slate-400'}`}>
                  <div className="aspect-square overflow-hidden rounded bg-slate-100"><img src={skin.asset_path} alt={`${skin.display_name} - Website ORB appearance skin`} className="h-full w-full object-contain" /></div>
                  <div className="mt-3 flex items-start justify-between gap-2"><span className="text-sm font-bold text-slate-900">{skin.display_name}</span>{selected && <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" />}</div>
                  {skin.factory_default && <p className="mt-1 text-xs text-slate-500">Verified fallback</p>}
                </button>
              );
            })}
          </div>
          {selectedSkin && <p className="mt-4 text-sm font-semibold text-slate-700">Selected: {selectedSkin.display_name}</p>}
        </section>
      )}

      {tab === 'models' && (
        <section className="max-w-5xl">
          <h2 className="text-2xl font-bold text-slate-950">LLM runtime</h2>
          <p className="mt-2 text-sm text-slate-600">Choose the owner model source. API keys stay on the backend as environment variable references.</p>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {dock.llm_options.map((option) => (
              <button key={option.id} onClick={() => selectProvider(option.id)} className={`rounded-md border bg-white p-4 text-left ${draft.llm.provider === option.id ? 'border-brand-orange ring-2 ring-brand-orange/20' : 'border-slate-200'}`}>
                <div className="flex items-center justify-between gap-3"><h3 className="font-bold text-slate-950">{option.label}</h3>{draft.llm.provider === option.id && <CheckCircle2 className="h-5 w-5 text-emerald-600" />}</div>
                <p className="mt-2 text-sm text-slate-600">{option.description}</p>
              </button>
            ))}
          </div>
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="rounded-md border border-slate-200 bg-white p-5">
              <h3 className="font-bold text-slate-950">Model settings</h3>
              <div className="mt-4 grid gap-4">
                <label className={labelClass}>Model
                  <input className={inputClass} value={draft.llm.model || ''} disabled={draft.llm.provider === 'runtime_default'} onChange={(event) => updateLlm({ model: event.target.value || null })} placeholder={draft.llm.provider === 'runtime_default' ? 'Runtime configured model' : 'Model name'} />
                </label>
                {draft.llm.provider === 'openai_compatible' && (
                  <label className={labelClass}>Base URL
                    <input className={inputClass} value={draft.llm.base_url || ''} onChange={(event) => updateLlm({ base_url: event.target.value || null })} placeholder="http://127.0.0.1:11434/v1" />
                  </label>
                )}
                {draft.llm.provider !== 'runtime_default' && draft.llm.provider !== 'ollama_local' && (
                  <label className={labelClass}>API key environment variable
                    <input className={inputClass} value={draft.llm.api_key_env || ''} onChange={(event) => updateLlm({ api_key_env: event.target.value.toUpperCase() || null })} placeholder="OPENAI_API_KEY" />
                  </label>
                )}
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className={labelClass}>Temperature
                    <input type="number" min="0" max="1.5" step="0.05" className={inputClass} value={draft.llm.temperature} onChange={(event) => updateLlm({ temperature: Number(event.target.value) })} />
                  </label>
                  <label className={labelClass}>Max output tokens
                    <input type="number" min="16" max="1200" step="16" className={inputClass} value={draft.llm.max_output_tokens} onChange={(event) => updateLlm({ max_output_tokens: Number(event.target.value) })} />
                  </label>
                </div>
              </div>
            </div>
            <div className="rounded-md border border-slate-200 bg-white p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><h3 className="font-bold text-slate-950">Local Ollama</h3><p className="mt-1 text-sm text-slate-600">{ollama?.message || 'Checking the configured local runtime...'}</p></div>
              <button onClick={() => projectId && api.getOrbDockOllama(projectId).then(setOllama)} className="rounded-md border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50">Refresh</button>
            </div>
            {ollama?.reachable && (
              <label className={`${labelClass} mt-4`}>Installed model
                <select className={inputClass} value={draft.llm.model || ''} onChange={(event) => updateDraft((current) => ({ ...current, llm: { ...current.llm, provider: 'ollama_local', model: event.target.value || null } }))}>
                  <option value="">Select a model</option>
                  {ollama.models.map((model) => <option key={model.name} value={model.name}>{model.name} · {(model.size / 1_073_741_824).toFixed(1)} GB</option>)}
                </select>
              </label>
            )}
            <div className="mt-4 flex flex-col gap-2 sm:flex-row">
              <input className={`${inputClass} mt-0`} value={pullModel} onChange={(event) => setPullModel(event.target.value)} placeholder="Model name, for example qwen3:8b" />
              <button onClick={() => void pull()} disabled={!ollama?.reachable || !pullModel.trim() || working === 'pull'} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-md bg-brand-orange px-4 py-2.5 text-sm font-bold text-brand-dark hover:bg-brand-accent hover:text-white disabled:opacity-45">
                {working === 'pull' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />} Download with Ollama
              </button>
            </div>
            </div>
          </div>
        </section>
      )}

      {tab === 'objectives' && (
        <section>
          <div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-2xl font-bold text-slate-950">Business objectives</h2><p className="mt-2 text-sm text-slate-600">Each outcome is bound to completion evidence, allowed destinations, tools, and explicit success or failure.</p></div><button onClick={() => updateDraft((current) => ({ ...current, business_objectives: [...current.business_objectives, blankObjective()] }))} className="inline-flex items-center gap-2 rounded-md bg-brand-dark px-4 py-2.5 text-sm font-bold text-white"><Plus className="h-4 w-4" /> Add objective</button></div>
          <div className="mt-5 space-y-4">
            {draft.business_objectives.map((objective, index) => (
              <article key={objective.objective_id} className="rounded-md border border-slate-200 bg-white p-5">
                <div className="flex items-center justify-between gap-3"><Toggle checked={objective.enabled} onChange={(enabled) => updateObjective(index, { enabled })} label="Enabled" /><button title="Remove objective" onClick={() => updateDraft((current) => ({ ...current, business_objectives: current.business_objectives.filter((_, itemIndex) => itemIndex !== index) }))} className="rounded p-2 text-slate-500 hover:bg-red-50 hover:text-red-700"><Trash2 className="h-4 w-4" /></button></div>
                <div className="mt-4 grid gap-4 md:grid-cols-2"><label className={labelClass}>Objective name<input className={inputClass} value={objective.name} onChange={(event) => updateObjective(index, { name: event.target.value })} placeholder="Schedule an appointment" /></label><label className={labelClass}>Escalation route<input className={inputClass} value={objective.escalation_route} onChange={(event) => updateObjective(index, { escalation_route: event.target.value })} placeholder="/contact or staff queue" /></label><ListField label="Completion evidence" value={objective.completion_evidence} onChange={(completion_evidence) => updateObjective(index, { completion_evidence })} /><ListField label="Required fields" value={objective.required_fields} onChange={(required_fields) => updateObjective(index, { required_fields })} /><ListField label="Permitted routes" value={objective.permitted_routes} onChange={(permitted_routes) => updateObjective(index, { permitted_routes })} placeholder="/appointments" /><ListField label="Permitted tools" value={objective.permitted_tools} onChange={(permitted_tools) => updateObjective(index, { permitted_tools })} placeholder="Use IDs from compiled Site World" /><TextAreaField label="Success condition" value={objective.success_condition} onChange={(success_condition) => updateObjective(index, { success_condition })} /><TextAreaField label="Failure condition" value={objective.failure_condition} onChange={(failure_condition) => updateObjective(index, { failure_condition })} /></div>
              </article>
            ))}
            {!draft.business_objectives.length && <p className="rounded-md border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">No owner objectives have been defined.</p>}
          </div>
        </section>
      )}

      {tab === 'additional' && (
        <section>
          <div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-2xl font-bold text-slate-950">Additional Guide Rails</h2><p className="mt-2 text-sm text-slate-600">Direct the ORB with structured behavior, evidence, action, and escalation rules.</p></div><button onClick={() => updateDraft((current) => ({ ...current, additional_guide_rails: [...current.additional_guide_rails, blankAdditionalRail()] }))} className="inline-flex items-center gap-2 rounded-md bg-brand-dark px-4 py-2.5 text-sm font-bold text-white"><Plus className="h-4 w-4" /> Add Guide Rail</button></div>
          <div className="mt-5 space-y-4">
            {draft.additional_guide_rails.map((rail, index) => (
              <article key={rail.guide_rail_id} className="rounded-md border border-slate-200 bg-white p-5">
                <div className="flex items-center justify-between gap-3"><Toggle checked={rail.enabled} onChange={(enabled) => updateAdditional(index, { enabled })} label="Enabled" /><button title="Remove Guide Rail" onClick={() => updateDraft((current) => ({ ...current, additional_guide_rails: current.additional_guide_rails.filter((_, itemIndex) => itemIndex !== index) }))} className="rounded p-2 text-slate-500 hover:bg-red-50 hover:text-red-700"><Trash2 className="h-4 w-4" /></button></div>
                <div className="mt-4 grid gap-4 md:grid-cols-2"><label className={labelClass}>Guide Rail name<input className={inputClass} value={rail.name} onChange={(event) => updateAdditional(index, { name: event.target.value })} placeholder="Financing conversation" /></label><PriorityField value={rail.priority} onChange={(priority) => updateAdditional(index, { priority })} /><TextAreaField label="Applies when" value={rail.applies_when} onChange={(applies_when) => updateAdditional(index, { applies_when })} /><TextAreaField label="ORB should" value={rail.orb_should} onChange={(orb_should) => updateAdditional(index, { orb_should })} /><TextAreaField label="ORB must not" value={rail.orb_must_not} onChange={(orb_must_not) => updateAdditional(index, { orb_must_not })} /><TextAreaField label="Escalate when" value={rail.escalate_when} onChange={(escalate_when) => updateAdditional(index, { escalate_when })} /><ListField label="Permitted actions" value={rail.permitted_actions} onChange={(permitted_actions) => updateAdditional(index, { permitted_actions })} /><ListField label="Required evidence" value={rail.required_evidence} onChange={(required_evidence) => updateAdditional(index, { required_evidence })} /><label className={labelClass}>Effective from<input type="date" className={inputClass} value={rail.effective_from || ''} onChange={(event) => updateAdditional(index, { effective_from: event.target.value || null })} /></label><label className={labelClass}>Effective until<input type="date" className={inputClass} value={rail.effective_until || ''} onChange={(event) => updateAdditional(index, { effective_until: event.target.value || null })} /></label><div className="md:col-span-2"><TextAreaField label="Owner note" hint="(internal only)" value={rail.owner_note} onChange={(owner_note) => updateAdditional(index, { owner_note })} /></div></div>
              </article>
            ))}
            {!draft.additional_guide_rails.length && <p className="rounded-md border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">No Additional Guide Rails have been defined.</p>}
          </div>
        </section>
      )}

      {tab === 'situational' && (
        <section>
          <div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-2xl font-bold text-slate-950">Situational Guide Rails</h2><p className="mt-2 text-sm text-slate-600">These rules activate only when their compiled route, visitor, workflow, confidence, or business condition matches.</p></div><button onClick={() => updateDraft((current) => ({ ...current, situational_guide_rails: [...current.situational_guide_rails, blankSituationalRail()] }))} className="inline-flex items-center gap-2 rounded-md bg-brand-dark px-4 py-2.5 text-sm font-bold text-white"><Plus className="h-4 w-4" /> Add situation</button></div>
          <div className="mt-5 space-y-4">
            {draft.situational_guide_rails.map((rail, index) => {
              const condition = (patch: Partial<DockSituationalGuideRail['conditions']>) => updateSituational(index, { conditions: { ...rail.conditions, ...patch } });
              return (
                <article key={rail.guide_rail_id} className="rounded-md border border-slate-200 bg-white p-5">
                  <div className="flex items-center justify-between gap-3"><Toggle checked={rail.enabled} onChange={(enabled) => updateSituational(index, { enabled })} label="Enabled" /><button title="Remove situational Guide Rail" onClick={() => updateDraft((current) => ({ ...current, situational_guide_rails: current.situational_guide_rails.filter((_, itemIndex) => itemIndex !== index) }))} className="rounded p-2 text-slate-500 hover:bg-red-50 hover:text-red-700"><Trash2 className="h-4 w-4" /></button></div>
                  <div className="mt-4 grid gap-4 md:grid-cols-2"><label className={labelClass}>Guide Rail name<input className={inputClass} value={rail.name} onChange={(event) => updateSituational(index, { name: event.target.value })} /></label><PriorityField value={rail.priority} onChange={(priority) => updateSituational(index, { priority })} /><ListField label="Current pages" value={rail.conditions.current_pages} onChange={(current_pages) => condition({ current_pages })} placeholder="/products" /><ListField label="Visitor types" value={rail.conditions.visitor_types} onChange={(visitor_types) => condition({ visitor_types })} /><ListField label="Workflow stages" value={rail.conditions.workflow_stages} onChange={(workflow_stages) => condition({ workflow_stages })} /><ListField label="Product categories" value={rail.conditions.product_categories} onChange={(product_categories) => condition({ product_categories })} /><ListField label="Business hours" value={rail.conditions.business_hours} onChange={(business_hours) => condition({ business_hours })} placeholder="Mon-Fri 09:00-17:00 America/Chicago" /><ListField label="Geographic eligibility" value={rail.conditions.geographic_eligibility} onChange={(geographic_eligibility) => condition({ geographic_eligibility })} /><ListField label="Active promotions" value={rail.conditions.active_promotions} onChange={(active_promotions) => condition({ active_promotions })} /><ListField label="Prior history terms" value={rail.conditions.prior_history_terms} onChange={(prior_history_terms) => condition({ prior_history_terms })} /><label className={labelClass}>Minimum confidence<input type="number" min="0" max="1" step="0.05" className={inputClass} value={rail.conditions.minimum_confidence ?? ''} onChange={(event) => condition({ minimum_confidence: event.target.value === '' ? null : Number(event.target.value) })} /></label><div><p className={labelClass}>Authentication state</p><div className="mt-3 flex flex-wrap gap-4">{(['anonymous', 'authenticated'] as const).map((state) => <Toggle key={state} label={state} checked={rail.conditions.authentication_states.includes(state)} onChange={(checked) => condition({ authentication_states: checked ? [...rail.conditions.authentication_states, state] : rail.conditions.authentication_states.filter((item) => item !== state) })} />)}</div></div><TextAreaField label="ORB should" value={rail.orb_should} onChange={(orb_should) => updateSituational(index, { orb_should })} /><TextAreaField label="ORB must not" value={rail.orb_must_not} onChange={(orb_must_not) => updateSituational(index, { orb_must_not })} /><ListField label="Permitted actions" value={rail.permitted_actions} onChange={(permitted_actions) => updateSituational(index, { permitted_actions })} /><ListField label="Required evidence" value={rail.required_evidence} onChange={(required_evidence) => updateSituational(index, { required_evidence })} /><TextAreaField label="Escalate when" value={rail.escalate_when} onChange={(escalate_when) => updateSituational(index, { escalate_when })} /><TextAreaField label="Owner note" hint="(internal only)" value={rail.owner_note} onChange={(owner_note) => updateSituational(index, { owner_note })} /></div>
                </article>
              );
            })}
            {!draft.situational_guide_rails.length && <p className="rounded-md border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">No situational Guide Rails have been defined.</p>}
          </div>
        </section>
      )}
    </div>
  );
};

export default OrbDockStationPage;
