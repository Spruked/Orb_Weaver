import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Activity,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Clock3,
  Download,
  Eye,
  FileText,
  Globe2,
  Layers3,
  MapPinned,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  Wrench
} from 'lucide-react';
import IssueCard from '../components/IssueCard';
import OrbAssemblyStatus from '../components/OrbAssemblyStatus';
import AuditChangeSummary from '../components/AuditChangeSummary';
import {
  api,
  AuditDelta,
  AuditReportPayload,
  AuditReportResponse,
  CrawlJob,
  Customer,
  downloads,
  GA4FullReport,
  openFiles,
  PreflightReport,
  Project
} from '../services/api';
import { canonicalOrbBaseUrl, setActiveOrbProjectContext } from '../orb/activeProjectContext';

const ACTIVE_CRAWL_STATUSES = new Set(['pending', 'running']);

type DashboardPayload = {
  project: Project;
  crawl_summary?: Record<string, number | boolean> | null;
  latest_crawl?: CrawlJob | null;
  audit_delta?: AuditDelta | null;
  latest_audit?: AuditReportResponse | null;
  audit_scores?: Record<string, number> | null;
  audit_issues?: AuditReportPayload['summary'] | null;
  ga4_data?: GA4FullReport | null;
  top_issues?: AuditReportPayload['top_issues'] | null;
};

interface DashboardProps {
  customer: Customer;
}

const scoreLabel = (key: string) => key.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());

const metricTone = (score: number) => {
  if (score >= 80) return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  if (score >= 60) return 'border-blue-200 bg-blue-50 text-blue-700';
  if (score >= 40) return 'border-amber-200 bg-amber-50 text-amber-700';
  return 'border-red-200 bg-red-50 text-red-700';
};

const DataTile: React.FC<{ label: string; value: React.ReactNode; note?: string }> = ({ label, value, note }) => (
  <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
    <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</p>
    <p className="mt-2 text-2xl font-bold text-slate-950">{value}</p>
    {note && <p className="mt-1 text-xs text-slate-500">{note}</p>}
  </div>
);

const siteReviewPanels = [
  ['What Site Review includes', 'Public crawl evidence, final audit results, route classification, technical and content issues, report exports, pointer coverage, and ORB integration readiness.'],
  ['How it differs from Public Preflight', 'Preflight is a public fit check. Site Review uses authenticated project evidence, deeper crawl and audit records, downloadable reports, and readiness gates.'],
  ['How findings are prioritized', 'Findings are grouped as critical items, warnings, and opportunities. Each item should explain what was found, why it matters, affected pages when available, and the recommended next action.'],
  ['How it connects to ORB readiness', 'Preflight, crawl, final audit, and pointer evidence determine whether ORB integration review can proceed and where visitor guidance needs owner review.'],
];

const EmptyDashboard: React.FC<{
  domain: string;
  competitorDomains: string;
  includeAdminSections: boolean;
  isCrawling: boolean;
  error: string;
  onDomainChange: (value: string) => void;
  onCompetitorsChange: (value: string) => void;
  onIncludeAdminChange: (value: boolean) => void;
  onStart: () => void;
}> = ({
  domain,
  competitorDomains,
  includeAdminSections,
  isCrawling,
  error,
  onDomainChange,
  onCompetitorsChange,
  onIncludeAdminChange,
  onStart
}) => (
  <section className="rounded-2xl bg-gradient-to-br from-brand-dark to-brand-blue p-6 text-white shadow-lg md:p-8">
    <p className="text-sm font-bold uppercase tracking-[0.16em] text-cyan-200">Website Audit</p>
    <h1 className="mt-2 text-3xl font-bold">Complete a full website crawl and audit before selecting an ORB package.</h1>
    <p className="mt-2 max-w-2xl text-sm text-slate-200">
      Orb Weaver will analyze the website, compile the available findings, and display the complete results here.
      Review the audit, website structure, pointer readiness, and ORB integration requirements before continuing.
    </p>
    <div className="mt-7 grid gap-3 lg:grid-cols-[1fr_1fr_auto]">
      <label className="relative">
        <span className="sr-only">Website URL</span>
        <Globe2 className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
        <input
          value={domain}
          onChange={(event) => onDomainChange(event.target.value)}
          placeholder="Website URL"
          className="w-full rounded-xl border border-white/20 bg-white/10 py-3.5 pl-12 pr-4 text-white placeholder:text-slate-400 focus:border-brand-orange focus:outline-none"
        />
      </label>
      <label>
        <span className="sr-only">Competitor domains</span>
        <input
          value={competitorDomains}
          onChange={(event) => onCompetitorsChange(event.target.value)}
          placeholder="Optional competitors, comma-separated"
          className="w-full rounded-xl border border-white/20 bg-white/10 px-4 py-3.5 text-white placeholder:text-slate-400 focus:border-brand-orange focus:outline-none"
        />
      </label>
      <button
        onClick={onStart}
        disabled={isCrawling || !domain.trim()}
        className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-orange px-6 py-3.5 font-bold text-brand-dark transition hover:bg-brand-accent hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isCrawling ? <Activity className="h-5 w-5 animate-pulse" /> : <Search className="h-5 w-5" />}
        {isCrawling ? 'Starting…' : 'Start Website Audit'}
      </button>
    </div>
    <label className="mt-4 inline-flex items-start gap-3 rounded-xl border border-white/15 bg-white/10 px-4 py-3 text-sm">
      <input
        type="checkbox"
        checked={includeAdminSections}
        onChange={(event) => onIncludeAdminChange(event.target.checked)}
        className="mt-1 rounded border-white/30 text-brand-orange focus:ring-brand-orange"
      />
      <span>
        <span className="block font-semibold">Include verified admin routes</span>
        <span className="block text-xs text-slate-300">Private routes inform ORB awareness but remain outside public SEO scoring.</span>
      </span>
    </label>
    {error && <p className="mt-4 text-sm font-semibold text-red-200">{error}</p>}
  </section>
);

const Dashboard: React.FC<DashboardProps> = ({ customer }) => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedProjectId = searchParams.get('project') || '';
  const [projects, setProjects] = useState<Project[]>([]);
  const [dashboardData, setDashboardData] = useState<DashboardPayload | null>(null);
  const [preflightReport, setPreflightReport] = useState<PreflightReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCrawling, setIsCrawling] = useState(false);
  const [isRunningPreflight, setIsRunningPreflight] = useState(false);
  const [isStartingAudit, setIsStartingAudit] = useState(false);
  const [domain, setDomain] = useState('');
  const [competitorDomains, setCompetitorDomains] = useState('');
  const [includeAdminSections, setIncludeAdminSections] = useState(true);
  const [error, setError] = useState('');

  const loadDashboard = useCallback(async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    setError('');
    try {
      const projectList = await api.listProjects();
      setProjects(projectList);
      const requested = projectList.find((project) => project.id === requestedProjectId);
      const latestAudited = [...projectList].reverse().find((project) => project.latest_audit_id);
      const selected = requested || latestAudited || projectList[projectList.length - 1];
      if (!selected) {
        setDashboardData(null);
        setPreflightReport(null);
        return;
      }
      if (selected.id !== requestedProjectId) {
        setSearchParams({ project: selected.id }, { replace: true });
      }
      const [combined, preflight] = await Promise.all([
        api.getCombinedDashboard(selected.id),
        api.getProjectPreflight(selected.id).catch(() => null)
      ]);
      setDashboardData(combined);
      setPreflightReport(preflight);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      if (showLoading) setIsLoading(false);
    }
  }, [requestedProjectId, setSearchParams]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const project = dashboardData?.project || projects.find((item) => item.id === requestedProjectId) || null;
  const audit = dashboardData?.latest_audit || null;
  const report = audit?.report || null;
  const scores = report?.scores || dashboardData?.audit_scores || null;
  const summary = report?.summary || dashboardData?.audit_issues || null;
  const pointerSummary = report?.pointer_summary;
  const plannedToolCalls = report?.planned_tool_calls || [];
  const allIssues = useMemo(() => report ? [
    ...report.issues.critical,
    ...report.issues.warnings,
    ...report.issues.opportunities
  ] : [], [report]);
  const sessions = Number(dashboardData?.ga4_data?.traffic_overview?.totals?.sessions || 0);
  const activeCrawl = !!project?.latest_crawl_status && ACTIVE_CRAWL_STATUSES.has(project.latest_crawl_status);

  useEffect(() => {
    if (!project?.domain) return;
    setActiveOrbProjectContext({
      project_id: String(project.id),
      canonical_domain: project.domain,
      canonical_base_url: canonicalOrbBaseUrl(project.domain),
      selected_crawl_job_id: project.latest_crawl_id || dashboardData?.latest_crawl?.id || null,
      active_customer_route: '/',
    });
  }, [dashboardData?.latest_crawl?.id, project]);
  const assemblyStatus = dashboardData?.latest_crawl?.assembly_status || null;
  const auditDelta = dashboardData?.audit_delta || null;

  useEffect(() => {
    if (!activeCrawl || !project) return;
    const timer = window.setInterval(() => loadDashboard(false), 4000);
    return () => window.clearInterval(timer);
  }, [activeCrawl, loadDashboard, project]);

  const handleStartCrawl = async () => {
    if (!domain.trim()) return;
    setIsCrawling(true);
    setError('');
    try {
      const normalizedDomain = domain.trim().replace(/^https?:\/\//, '').replace(/\/$/, '');
      const createdProject = await api.createProject({ domain: normalizedDomain, ga4_property_id: null });
      const crawl = await api.startCrawl(createdProject.id, {
        max_pages: 150,
        delay: 1.5,
        max_depth: 5,
        competitor_domains: competitorDomains.split(',').map((item) => item.trim()).filter(Boolean),
        seed_urls: includeAdminSections ? ['/admin'] : [],
        include_admin_sections: includeAdminSections
      });
      navigate(`/crawl/${crawl.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start crawl');
    } finally {
      setIsCrawling(false);
    }
  };

  const handleRunPreflight = async () => {
    if (!project) return;
    setIsRunningPreflight(true);
    setError('');
    try {
      setPreflightReport(await api.runProjectPreflight(project.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run preflight scan');
    } finally {
      setIsRunningPreflight(false);
    }
  };

  const handleRunFinalAudit = async () => {
    if (!project) return;
    setIsStartingAudit(true);
    setError('');
    try {
      const nextAudit = await api.reauditProject(project.id);
      navigate(`/audit/${nextAudit.audit_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start the final audit');
    } finally {
      setIsStartingAudit(false);
    }
  };

  if (isLoading) {
    return <div className="card text-slate-500">Loading the completed audit and website evidence…</div>;
  }

  if (!project || !audit || !report || !summary || !scores) {
    return (
      <div className="space-y-6">
        {projects.length > 0 && (
          <div className="card flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Selected website</p>
              <p className="font-bold text-slate-950">{project?.name || customer.business_name}</p>
            </div>
            <select
              value={project?.id || requestedProjectId}
              onChange={(event) => setSearchParams({ project: event.target.value })}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-800"
            >
              {projects.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.domain}</option>)}
            </select>
          </div>
        )}
        {activeCrawl && (
          <div className="card border-blue-200 bg-blue-50">
            <div className="flex items-center gap-3">
              <Activity className="h-5 w-5 animate-pulse text-blue-700" />
              <div>
                <p className="font-bold text-slate-950">Website crawl in progress</p>
                <p className="text-sm text-slate-600">The dashboard will populate after the audit compiles.</p>
              </div>
            </div>
          </div>
        )}
        <OrbAssemblyStatus assembly={assemblyStatus} />
        <EmptyDashboard
          domain={domain}
          competitorDomains={competitorDomains}
          includeAdminSections={includeAdminSections}
          isCrawling={isCrawling}
          error={error}
          onDomainChange={setDomain}
          onCompetitorsChange={setCompetitorDomains}
          onIncludeAdminChange={setIncludeAdminSections}
          onStart={handleStartCrawl}
        />
      </div>
    );
  }

  const routeCounts = summary.route_category_counts || {};
  const targetCounts = pointerSummary?.target_type_counts || {};
  const integrationGroups = plannedToolCalls.reduce<Record<string, number>>((groups, tool) => {
    groups[tool.tool] = (groups[tool.tool] || 0) + 1;
    return groups;
  }, {});
  const publicPages = summary.public_pages ?? summary.total_pages;
  const excludedPages = summary.pages_excluded_from_public_seo_scoring || 0;
  const preflightComplete = Boolean(preflightReport && preflightReport.status !== 'not_run' && (preflightReport.pages_scanned || 0) > 0);
  const crawlComplete = project.latest_crawl_status === 'completed';
  const auditComplete = Boolean(project.latest_audit_id && audit.report);

  return (
    <div className="space-y-7">
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 bg-slate-950 px-5 py-5 text-white md:px-7">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-300">Completed audit results</p>
              <h1 className="mt-2 text-3xl font-bold">{project.name}</h1>
              <p className="mt-1 text-slate-300">{project.domain}</p>
              <p className="mt-3 text-sm text-slate-400">
                Audit #{audit.id} · {new Date(audit.created_at).toLocaleString()} · {summary.total_pages} pages examined
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <select
                value={project.id}
                onChange={(event) => setSearchParams({ project: event.target.value })}
                className="rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm font-semibold text-white"
                aria-label="Choose audited website"
              >
                {projects.map((item) => <option key={item.id} value={item.id} className="text-slate-950">{item.name} · {item.domain}</option>)}
              </select>
              <button onClick={() => navigate(`/audit/${audit.id}`)} className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm font-bold hover:bg-white/20">
                <Eye className="h-4 w-4" /> Full audit
              </button>
              <button onClick={() => downloads.auditCsv(audit.id)} className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm font-bold hover:bg-white/20">
                <Download className="h-4 w-4" /> CSV
              </button>
              <button onClick={() => openFiles.auditPdf(audit.id)} className="inline-flex items-center gap-2 rounded-lg bg-brand-orange px-3 py-2 text-sm font-bold text-brand-dark hover:bg-brand-accent hover:text-white">
                <FileText className="h-4 w-4" /> Open report
              </button>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-4">
          <div className="border-b border-slate-200 p-5 md:border-b-0 md:border-r">
            <div className="flex items-center gap-3">
              <span className={`flex h-9 w-9 items-center justify-center rounded-full font-bold ${preflightComplete ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>1</span>
              <div><p className="font-bold text-slate-950">Preflight</p><p className={`text-xs ${preflightComplete ? 'text-emerald-700' : 'text-amber-700'}`}>{preflightComplete ? 'Complete' : 'Required'}</p></div>
            </div>
          </div>
          <div className="border-b border-slate-200 p-5 md:border-b-0 md:border-r">
            <div className="flex items-center gap-3">
              <span className={`flex h-9 w-9 items-center justify-center rounded-full font-bold ${crawlComplete ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>2</span>
              <div><p className="font-bold text-slate-950">Crawl</p><p className={`text-xs ${crawlComplete ? 'text-emerald-700' : 'text-slate-500'}`}>{crawlComplete ? 'Complete' : 'Required'}</p></div>
            </div>
          </div>
          <div className="border-b border-slate-200 p-5 md:border-b-0 md:border-r">
            <div className="flex items-center gap-3">
              <span className={`flex h-9 w-9 items-center justify-center rounded-full font-bold ${auditComplete ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>3</span>
              <div><p className="font-bold text-slate-950">Final Audit</p><p className={`text-xs ${auditComplete ? 'text-emerald-700' : 'text-slate-500'}`}>{auditComplete ? 'Complete' : 'Required'}</p></div>
            </div>
          </div>
          <div className={`p-5 ${preflightComplete && crawlComplete && auditComplete ? 'bg-cyan-50' : ''}`}>
            <div className="flex items-center gap-3">
              <span className={`flex h-9 w-9 items-center justify-center rounded-full font-bold ${preflightComplete && crawlComplete && auditComplete ? 'bg-brand-accent text-white' : 'bg-slate-100 text-slate-500'}`}>4</span>
              <div><p className="font-bold text-slate-950">ORBS</p><p className={`text-xs ${preflightComplete && crawlComplete && auditComplete ? 'font-semibold text-brand-blue' : 'text-slate-500'}`}>{preflightComplete && crawlComplete && auditComplete ? 'Ready for integration review' : 'Locked until evidence is complete'}</p></div>
            </div>
          </div>
        </div>
      </section>

      {error && <div className="card border-red-200 bg-red-50 text-sm font-semibold text-red-700">{error}</div>}

      <OrbAssemblyStatus assembly={assemblyStatus} />
      <AuditChangeSummary delta={auditDelta} />

      <section className="card">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Site Review</p>
            <h2 className="mt-1 text-xl font-bold text-slate-950">Evidence-backed website review</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Site Review turns this project&apos;s crawl, final audit, reports, route categories, pointer map, and
              preflight readiness into a practical website assessment. It summarizes existing evidence and does not
              promise findings the scan or audit did not produce.
            </p>
          </div>
          <button onClick={() => navigate(`/reports/${project.id}`)} className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50">
            Review report files <FileText className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {siteReviewPanels.map(([title, body]) => (
            <article key={title} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <h3 className="text-sm font-bold text-slate-950">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section aria-labelledby="score-heading" className="card">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Audit health</p>
            <h2 id="score-heading" className="mt-1 text-xl font-bold text-slate-950">Complete scorecard</h2>
          </div>
          <p className="text-sm text-slate-500">Every scoring category returned by the audit</p>
        </div>
        <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
          {Object.entries(scores).map(([key, value]) => (
            <div key={key} className={`rounded-xl border p-4 ${metricTone(value)}`}>
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-bold uppercase tracking-[0.08em]">{scoreLabel(key)}</p>
                {key === 'overall' && <Sparkles className="h-4 w-4" />}
              </div>
              <p className="mt-2 text-3xl font-bold">{Math.round(value)}</p>
              <p className="text-xs opacity-75">out of 100</p>
            </div>
          ))}
        </div>
      </section>

      <section aria-labelledby="evidence-heading">
        <div className="mb-4">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Website evidence</p>
          <h2 id="evidence-heading" className="mt-1 text-xl font-bold text-slate-950">What the audit examined</h2>
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <DataTile label="Total pages" value={summary.total_pages} note="All routes examined" />
          <DataTile label="Public pages" value={publicPages} note="Included in public scoring" />
          <DataTile label="Protected routes" value={excludedPages} note="Used for ORB awareness only" />
          <DataTile label="Average load" value={summary.avg_load_time ? `${(summary.avg_load_time / 1000).toFixed(2)}s` : '—'} />
          <DataTile label="Context entities" value={summary.orb_context_entities ?? '—'} note="Detected site concepts" />
          <DataTile label="Thin pages" value={summary.orb_context_thin_content_pages ?? '—'} note="Low-context routes" />
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="card">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Findings</p>
              <h2 className="mt-1 text-xl font-bold text-slate-950">Issues by severity</h2>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-bold text-slate-700">{summary.total_issues} total</span>
          </div>
          <div className="mt-5 grid grid-cols-3 gap-3">
            <div className="rounded-xl border border-red-200 bg-red-50 p-4"><p className="text-2xl font-bold text-red-700">{summary.critical_count}</p><p className="text-xs font-bold text-red-700">Critical</p></div>
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4"><p className="text-2xl font-bold text-amber-700">{summary.warning_count}</p><p className="text-xs font-bold text-amber-700">Warnings</p></div>
            <div className="rounded-xl border border-blue-200 bg-blue-50 p-4"><p className="text-2xl font-bold text-blue-700">{summary.opportunity_count}</p><p className="text-xs font-bold text-blue-700">Opportunities</p></div>
          </div>
          <div className="mt-5 max-h-[34rem] space-y-3 overflow-y-auto pr-1">
            {allIssues.length > 0 ? allIssues.map((issue, index) => <IssueCard key={`${issue.title}-${index}`} issue={issue} />) : (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-700">No audit issues were returned.</div>
            )}
          </div>
        </div>

        <div className="space-y-5">
          <div className="card">
            <div className="flex items-center gap-3">
              <MapPinned className="h-5 w-5 text-brand-accent" />
              <div><p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Route classification</p><h2 className="text-lg font-bold text-slate-950">Website areas</h2></div>
            </div>
            <div className="mt-4 space-y-3">
              {Object.keys(routeCounts).length > 0 ? Object.entries(routeCounts).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between gap-4 border-b border-slate-100 pb-2 last:border-0 last:pb-0">
                  <span className="text-sm font-medium capitalize text-slate-700">{key.replace(/_/g, ' ')}</span>
                  <span className="font-bold text-slate-950">{value}</span>
                </div>
              )) : <p className="text-sm text-slate-500">This audit predates route classification.</p>}
            </div>
          </div>

          <div className={`card ${pointerSummary?.status === 'passed' ? 'border-emerald-200' : 'border-amber-200'}`}>
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3"><Target className="h-5 w-5 text-brand-accent" /><div><p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Pointer map</p><h2 className="text-lg font-bold text-slate-950">Interaction coverage</h2></div></div>
              <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${pointerSummary?.status === 'passed' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{pointerSummary?.status || 'not available'}</span>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-3">
              <DataTile label="Pointers" value={pointerSummary?.record_count ?? 0} />
              <DataTile label="Routes" value={pointerSummary?.routes_with_pointers ?? 0} />
              <DataTile label="Duplicates" value={pointerSummary?.duplicate_target_ids ?? 0} />
            </div>
            {Object.keys(targetCounts).length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {Object.entries(targetCounts).map(([key, value]) => <span key={key} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold capitalize text-slate-700">{key.replace(/_/g, ' ')} {value}</span>)}
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="card">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="flex items-center gap-3">
            <Wrench className="h-5 w-5 text-brand-accent" />
            <div><p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Integration evidence</p><h2 className="text-xl font-bold text-slate-950">Planned support actions</h2></div>
          </div>
          <span className="rounded-full bg-violet-100 px-3 py-1 text-sm font-bold text-violet-700">{plannedToolCalls.length} planned calls</span>
        </div>
        <div className="mt-5 grid gap-5 lg:grid-cols-[0.7fr_1.3fr]">
          <div className="space-y-2">
            {Object.entries(integrationGroups).map(([tool, count]) => (
              <div key={tool} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2">
                <span className="text-sm font-semibold text-slate-700">{tool}</span><span className="font-bold text-slate-950">{count}</span>
              </div>
            ))}
            {plannedToolCalls.length === 0 && <p className="text-sm text-slate-500">No integration actions were generated.</p>}
          </div>
          <div className="max-h-96 overflow-y-auto rounded-xl border border-slate-200">
            {plannedToolCalls.map((tool) => (
              <div key={tool.id} className="grid gap-2 border-b border-slate-100 p-3 last:border-0 sm:grid-cols-[1fr_auto]">
                <div><p className="font-bold text-slate-900">{tool.tool}</p><p className="text-xs text-slate-500">{tool.purpose || tool.section || tool.trigger}</p>{tool.route && <p className="mt-1 truncate text-xs text-brand-blue">{tool.route}</p>}</div>
                <span className={`self-start rounded-full px-2.5 py-1 text-xs font-bold ${tool.requires_mcp ? 'bg-violet-100 text-violet-700' : 'bg-emerald-100 text-emerald-700'}`}>{tool.requires_mcp ? 'Approval gated' : tool.status}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="card">
        <div className="flex items-center gap-3"><Layers3 className="h-5 w-5 text-brand-accent" /><div><p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Prioritized response</p><h2 className="text-xl font-bold text-slate-950">Recommended action plan</h2></div></div>
        <div className="mt-5 grid gap-3 lg:grid-cols-2">
          {report.top_issues.map((issue, index) => (
            <div key={`${issue.title}-${index}`} className="flex gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <span className="flex h-8 w-8 flex-none items-center justify-center rounded-full bg-brand-orange text-sm font-bold text-brand-dark">{index + 1}</span>
              <div><h3 className="font-bold text-slate-950">{issue.title}</h3><p className="mt-1 text-sm text-slate-600">{issue.recommendation}</p><div className="mt-3 flex flex-wrap gap-2"><span className="rounded-full bg-white px-2.5 py-1 text-xs font-bold text-slate-700">Impact {issue.impact_score}</span><span className="rounded-full bg-white px-2.5 py-1 text-xs font-bold capitalize text-slate-700">{issue.severity}</span></div></div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-[1fr_auto]">
        <details className="card group">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
            <div className="flex items-center gap-3"><ShieldCheck className="h-5 w-5 text-brand-accent" /><div><p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Supporting check</p><h2 className="text-lg font-bold text-slate-950">Preflight readiness</h2></div></div>
            <span className="text-sm font-bold text-brand-blue">{preflightReport?.status && preflightReport.status !== 'not_run' ? `${preflightReport.pages_scanned || 0} pages checked` : 'Not run'}</span>
          </summary>
          <div className="mt-5 border-t border-slate-200 pt-5">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <DataTile label="Pages checked" value={preflightReport?.pages_scanned || 0} />
              <DataTile label="Confidence" value={preflightReport?.confidence == null ? '—' : `${Math.round(preflightReport.confidence * 100)}%`} />
              <DataTile label="Sitemap" value={preflightReport?.detected?.sitemap_xml ? 'Found' : 'Not found'} />
              <DataTile label="Warnings" value={preflightReport?.warnings?.length || 0} />
            </div>
            <button onClick={handleRunPreflight} disabled={isRunningPreflight} className="mt-4 inline-flex items-center gap-2 rounded-lg border border-cyan-200 bg-cyan-50 px-4 py-2 text-sm font-bold text-brand-blue hover:bg-cyan-100 disabled:opacity-50">
              {isRunningPreflight && <Activity className="h-4 w-4 animate-pulse" />}{isRunningPreflight ? 'Running…' : preflightReport?.status !== 'not_run' ? 'Re-run preflight' : 'Run preflight'}
            </button>
          </div>
        </details>

        <div className="rounded-2xl bg-slate-950 p-6 text-white shadow-sm lg:w-80">
          {preflightComplete && crawlComplete && auditComplete ? <CheckCircle2 className="h-7 w-7 text-emerald-400" /> : <Clock3 className="h-7 w-7 text-amber-300" />}
          <h2 className="mt-4 text-xl font-bold">
            {!preflightComplete ? 'Preflight is required' : !crawlComplete ? 'Crawl is required' : !auditComplete ? 'Final Audit is required' : 'Technical evidence is complete'}
          </h2>
          <p className="mt-2 text-sm text-slate-300">
            {!preflightComplete
              ? `Run Preflight for ${project.name} before the ORBS integration review can begin.`
              : !crawlComplete
                ? `Complete the project crawl before the Final Audit and ORBS integration review.`
                : !auditComplete
                  ? `Run the Final Audit before any package recommendation or purchase action is shown.`
                  : `Review the site-specific ORBS integration assessment for ${project.name}.`}
          </p>
          {!preflightComplete ? (
            <button onClick={handleRunPreflight} disabled={isRunningPreflight} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand-orange px-4 py-3 font-bold text-brand-dark hover:bg-brand-accent hover:text-white disabled:opacity-50">
              {isRunningPreflight && <Activity className="h-4 w-4 animate-pulse" />}{isRunningPreflight ? 'Running Preflight…' : 'Run Preflight'}
            </button>
          ) : !crawlComplete ? (
            <button onClick={() => navigate(`/projects?project=${encodeURIComponent(project.id)}`)} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand-orange px-4 py-3 font-bold text-brand-dark hover:bg-brand-accent hover:text-white">
              Run Crawl <ArrowRight className="h-4 w-4" />
            </button>
          ) : !auditComplete ? (
            <button onClick={handleRunFinalAudit} disabled={isStartingAudit} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand-orange px-4 py-3 font-bold text-brand-dark hover:bg-brand-accent hover:text-white disabled:opacity-50">
              {isStartingAudit && <Activity className="h-4 w-4 animate-pulse" />}{isStartingAudit ? 'Starting Final Audit…' : 'Run Final Audit'}
            </button>
          ) : (
            <button onClick={() => navigate(`/orbs/${project.id}`)} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand-orange px-4 py-3 font-bold text-brand-dark hover:bg-brand-accent hover:text-white">
              Review ORBS Integration <ArrowRight className="h-4 w-4" />
            </button>
          )}
          <button onClick={() => navigate(`/reports/${project.id}`)} className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-white/20 px-4 py-2.5 text-sm font-bold hover:bg-white/10">
            Review report files <FileText className="h-4 w-4" />
          </button>
        </div>
      </section>

      {sessions > 0 && (
        <section className="card flex items-center justify-between gap-4">
          <div className="flex items-center gap-3"><BarChart3 className="h-5 w-5 text-emerald-600" /><div><p className="font-bold text-slate-950">Connected GA4 activity</p><p className="text-sm text-slate-500">{sessions.toLocaleString()} sessions in the current reporting window</p></div></div>
          <button onClick={() => navigate(project.ga4_property_id ? `/ga4/${project.ga4_property_id}` : '/ga4')} className="text-sm font-bold text-brand-blue">View analytics</button>
        </section>
      )}
    </div>
  );
};

export default Dashboard;
