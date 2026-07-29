import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  CheckCircle2,
  FileStack,
  Globe2,
  Layers3,
  ListChecks,
  Play,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import { api, CrawlConfig, Project } from '../services/api';

type ScanMode = 'full' | 'section' | 'exact' | 'changed';

type ModeDefinition = {
  id: ScanMode;
  label: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
};

const MODES: ModeDefinition[] = [
  {
    id: 'full',
    label: 'Full Site',
    title: 'Rebuild the complete website baseline',
    description: 'Crawl the full same-domain site, refresh every measured page, and produce a new complete Site World baseline.',
    icon: Globe2,
  },
  {
    id: 'section',
    label: 'Section',
    title: 'Refresh one or more website sections',
    description: 'Start from selected section paths and follow links only while they remain inside those approved path boundaries.',
    icon: Layers3,
  },
  {
    id: 'exact',
    label: 'Exact Pages',
    title: 'Scan only the pages you name',
    description: 'Measure the listed pages without following their links. Untouched pages are carried forward from the last baseline.',
    icon: ListChecks,
  },
  {
    id: 'changed',
    label: 'Changed Pages',
    title: 'Update pages changed since the last scan',
    description: 'Use this after editing a known set of pages. Only those URLs are replaced in the authoritative ORB context.',
    icon: RefreshCw,
  },
];

const STANDARD_CONTEXT_SEEDS = [
  '/', '/admin', '/admin/customers', '/dashboard', '/account', '/cart', '/checkout',
  '/checkout/success', '/login', '/signup', '/privacy', '/terms', '/sitemap.xml', '/robots.txt',
];

const splitEntries = (value: string): string[] => (
  value
    .split(/[\n,]+/)
    .map((entry) => entry.trim())
    .filter(Boolean)
);

const normalizeProjectEntry = (entry: string, project: Project): string | null => {
  if (!entry) return null;
  if (entry.startsWith('/')) return entry;
  try {
    const url = new URL(/^https?:\/\//i.test(entry) ? entry : `https://${project.domain}/${entry.replace(/^\/+/, '')}`);
    const projectHost = new URL(/^https?:\/\//i.test(project.domain) ? project.domain : `https://${project.domain}`).host;
    if (url.host !== projectHost) return null;
    return `${url.pathname || '/'}${url.search || ''}`;
  } catch {
    return null;
  }
};

const ScanCenter: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [mode, setMode] = useState<ScanMode>('full');
  const [targets, setTargets] = useState('');
  const [maxPages, setMaxPages] = useState(500);
  const [maxDepth, setMaxDepth] = useState(8);
  const [includeAdmin, setIncludeAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    api.listProjects()
      .then((rows) => {
        if (cancelled) return;
        setProjects(rows);
        setSelectedProjectId((current) => current || rows[0]?.id || '');
      })
      .catch((reason) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : 'Unable to load projects');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const selectedProject = projects.find((project) => project.id === selectedProjectId) || null;
  const selectedMode = MODES.find((definition) => definition.id === mode) || MODES[0];

  const normalizedTargets = useMemo(() => {
    if (!selectedProject || mode === 'full') return [];
    return Array.from(new Set(
      splitEntries(targets)
        .map((entry) => normalizeProjectEntry(entry, selectedProject))
        .filter((entry): entry is string => !!entry)
    ));
  }, [mode, selectedProject, targets]);

  const enteredTargetCount = splitEntries(targets).length;
  const invalidTargetCount = Math.max(enteredTargetCount - normalizedTargets.length, 0);
  const requiresTargets = mode !== 'full';
  const canStart = !!selectedProject && (!requiresTargets || normalizedTargets.length > 0) && !starting;

  const startScan = async () => {
    if (!selectedProject || !canStart) return;
    setError('');
    setStarting(true);
    try {
      const scopedSeeds = mode === 'full'
        ? STANDARD_CONTEXT_SEEDS
        : [`orb-scope:${mode}`, ...normalizedTargets];
      const config: CrawlConfig = {
        max_pages: mode === 'exact' || mode === 'changed'
          ? Math.max(normalizedTargets.length, 1)
          : Math.max(1, maxPages),
        delay: 1.5,
        max_depth: mode === 'exact' || mode === 'changed' ? 1 : Math.max(1, maxDepth),
        seed_urls: scopedSeeds,
        include_admin_sections: mode === 'full' ? includeAdmin : false,
      };
      const job = selectedProject.latest_crawl_id
        ? await api.recrawlProject(selectedProject.id, config)
        : await api.startCrawl(selectedProject.id, config);
      navigate(`/crawl/${job.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to start scan');
      setStarting(false);
    }
  };

  if (loading) {
    return <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-slate-500">Loading Scan Center…</div>;
  }

  return (
    <div className="space-y-5">
      <header className="rounded-2xl border border-slate-200 bg-white px-6 py-6 shadow-sm">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-extrabold uppercase tracking-[0.18em] text-brand-accent">Project Scan Center</p>
            <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-950">Choose exactly what Orb Weaver scans</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Full scans rebuild the baseline. Scoped scans refresh only approved sections or pages and carry every untouched page forward into the new authoritative Site World.
            </p>
          </div>
          <label className="min-w-0 lg:w-80">
            <span className="mb-2 block text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Project</span>
            <select
              value={selectedProjectId}
              onChange={(event) => setSelectedProjectId(event.target.value)}
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-bold text-slate-800 outline-none transition focus:border-brand-accent focus:ring-4 focus:ring-brand-orange/15"
            >
              {projects.map((project) => (
                <option key={project.id} value={project.id}>{project.name} · {project.domain}</option>
              ))}
            </select>
          </label>
        </div>
      </header>

      {error && <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-bold text-red-700">{error}</div>}

      {projects.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <FileStack className="mx-auto h-8 w-8 text-slate-300" />
          <h2 className="mt-3 font-bold text-slate-800">Create a project first</h2>
          <p className="mt-1 text-sm text-slate-500">Each hostname keeps its own scan history, Site World, pointer map, and audit evidence.</p>
          <button onClick={() => navigate('/projects')} className="mt-5 rounded-full bg-brand-dark px-5 py-2.5 text-sm font-bold text-white hover:bg-brand-accent">Open Projects</button>
        </section>
      ) : (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 bg-slate-50 px-4 py-4 sm:px-6">
            <div className="flex flex-wrap gap-2">
              {MODES.map(({ id, label, icon: Icon }) => {
                const active = mode === id;
                return (
                  <button
                    key={id}
                    onClick={() => setMode(id)}
                    className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-bold transition-all duration-200 ${active
                      ? 'border-brand-orange bg-brand-orange text-brand-dark shadow-sm'
                      : 'border-slate-300 bg-white text-slate-600 hover:-translate-y-0.5 hover:border-cyan-400 hover:bg-cyan-50 hover:text-cyan-800 hover:shadow-sm'}`}
                  >
                    <Icon className="h-4 w-4" /> {label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid gap-6 p-5 sm:p-6 xl:grid-cols-[minmax(0,1fr)_320px]">
            <div className="space-y-5">
              <div>
                <h2 className="text-2xl font-extrabold text-slate-950">{selectedMode.title}</h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{selectedMode.description}</p>
              </div>

              {mode !== 'full' && (
                <label className="block">
                  <span className="mb-2 block text-sm font-bold text-slate-800">
                    {mode === 'section' ? 'Section paths' : 'Page URLs or paths'}
                  </span>
                  <textarea
                    value={targets}
                    onChange={(event) => setTargets(event.target.value)}
                    rows={9}
                    placeholder={mode === 'section'
                      ? '/marketplace/products\n/marketplace/collection'
                      : '/marketplace/product/orb_robot_blue\nhttps://example.com/products/updated-item'}
                    className="w-full rounded-xl border border-slate-300 bg-slate-950 px-4 py-3 font-mono text-sm leading-6 text-cyan-100 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-400/10"
                  />
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
                    <span className="font-semibold text-emerald-700">{normalizedTargets.length} accepted</span>
                    {invalidTargetCount > 0 && <span className="font-semibold text-red-700">{invalidTargetCount} rejected as invalid or outside this project domain</span>}
                  </div>
                </label>
              )}

              <div className="grid gap-4 sm:grid-cols-2">
                {mode !== 'exact' && mode !== 'changed' && (
                  <label>
                    <span className="mb-2 block text-sm font-bold text-slate-800">Maximum pages</span>
                    <input type="number" min={1} max={5000} value={maxPages} onChange={(event) => setMaxPages(Number(event.target.value) || 1)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm font-bold outline-none focus:border-brand-accent focus:ring-4 focus:ring-brand-orange/15" />
                  </label>
                )}
                {mode !== 'exact' && mode !== 'changed' && (
                  <label>
                    <span className="mb-2 block text-sm font-bold text-slate-800">Link depth</span>
                    <input type="number" min={1} max={10} value={maxDepth} onChange={(event) => setMaxDepth(Number(event.target.value) || 1)} className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm font-bold outline-none focus:border-brand-accent focus:ring-4 focus:ring-brand-orange/15" />
                  </label>
                )}
              </div>

              {mode === 'full' && (
                <label className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold text-slate-700">
                  <input type="checkbox" checked={includeAdmin} onChange={(event) => setIncludeAdmin(event.target.checked)} className="h-4 w-4 rounded border-slate-300 text-brand-accent focus:ring-brand-accent" />
                  Include owner/admin awareness routes in the scan while keeping them excluded from public scoring
                </label>
              )}

              <button
                onClick={startScan}
                disabled={!canStart}
                className="inline-flex items-center gap-2 rounded-full bg-brand-dark px-6 py-3 text-sm font-extrabold text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-brand-accent hover:shadow-md disabled:cursor-not-allowed disabled:opacity-40"
              >
                {starting ? <Activity className="h-4 w-4 animate-pulse" /> : <Play className="h-4 w-4 fill-current" />}
                {starting ? 'Starting scan…' : `Run ${selectedMode.label} Scan`}
              </button>
            </div>

            <aside className="space-y-4">
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
                <div className="flex items-center gap-2 text-emerald-800"><ShieldCheck className="h-5 w-5" /><h3 className="font-extrabold">Authoritative merge rule</h3></div>
                <ul className="mt-4 space-y-3 text-sm leading-5 text-emerald-950">
                  <li className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> Selected pages are freshly measured.</li>
                  <li className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> Matching old page records are replaced.</li>
                  <li className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> Every untouched page is carried forward.</li>
                  <li className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> The pointer map rebuilds from the merged Site World.</li>
                </ul>
              </div>

              <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm leading-6 text-amber-950">
                <h3 className="font-extrabold">Separate hostname rule</h3>
                <p className="mt-2">
                  Campaign pages are not part of <strong>orbweaver.spruked.com</strong>. Create or select the campaign hostname as its own project, then scan its pages here. The campaign ORB can still use the Orb Weaver runtime without mixing the two sites’ evidence.
                </p>
              </div>
            </aside>
          </div>
        </section>
      )}
    </div>
  );
};

export default ScanCenter;
