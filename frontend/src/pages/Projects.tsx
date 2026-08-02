import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  Circle,
  ExternalLink,
  FileText,
  FolderPlus,
  Globe,
  MoreVertical,
  RotateCw,
  Search,
  ShieldCheck,
  Square,
  Trash2,
} from 'lucide-react';
import { api, CrawlJob, LifecycleJob, LifecycleJobType, PreflightReport, Project } from '../services/api';
import { canonicalOrbBaseUrl, setActiveOrbProjectContext } from '../orb/activeProjectContext';

const ACTIVE_CRAWL_STATUSES = new Set(['pending', 'running', 'cancel_requested']);
const ACTIVE_LIFECYCLE_STATUSES = new Set(['PENDING', 'RUNNING', 'CANCEL_REQUESTED']);
const LIFECYCLE_STAGES: Array<{ type: LifecycleJobType; label: string; automatic?: boolean }> = [
  { type: 'MAP_CRAWL', label: 'Map Crawl' },
  { type: 'SITE_SCAN', label: 'Site Scan' },
  { type: 'ORB_SCAN', label: 'ORB Scan' },
  { type: 'POINTER_RECOVERY', label: 'Pointer Recovery Pass', automatic: true },
  { type: 'FULL_AUDIT', label: 'Full Audit' },
];
const WEBSITE_CONTEXT_SEED_URLS = [
  '/', '/admin', '/admin/customers', '/dashboard', '/account', '/cart', '/checkout',
  '/checkout/success', '/login', '/signup', '/privacy', '/terms', '/sitemap.xml', '/robots.txt'
];

type ProjectTab = 'overview' | 'lifecycle' | 'preflight' | 'pointer' | 'jobs';
type ProjectStatusFilter = 'all' | 'active' | 'ready' | 'not-run' | 'failed';

const PROJECT_TABS: Array<{ id: ProjectTab; label: string }> = [
  { id: 'overview', label: 'Overview' },
  { id: 'lifecycle', label: 'Lifecycle' },
  { id: 'preflight', label: 'Preflight' },
  { id: 'pointer', label: 'Pointer Map' },
  { id: 'jobs', label: 'Jobs' },
];

const formatDateTime = (value?: string | null) => {
  if (!value) return 'Unavailable';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? 'Unavailable' : parsed.toLocaleString();
};

const formatElapsed = (start?: string | null, end?: string | null) => {
  if (!start) return 'Unavailable';
  const startTime = new Date(start).getTime();
  const endTime = end ? new Date(end).getTime() : Date.now();
  if (Number.isNaN(startTime) || Number.isNaN(endTime) || endTime < startTime) return 'Unavailable';
  const seconds = Math.floor((endTime - startTime) / 1000);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m`;
  return `${seconds}s`;
};

const formatConfidence = (report?: PreflightReport) => {
  if (!report || report.status === 'not_run' || report.confidence == null) return '—';
  return `${Math.round(report.confidence * 100)}%`;
};

const lifecycleStatusLabel = (job?: LifecycleJob) => {
  if (!job) return 'Not Run';
  if (job.status === 'PENDING') return 'Pending';
  if (job.status === 'RUNNING') return 'Running';
  if (job.status === 'CANCEL_REQUESTED') return 'Stopping';
  if (job.status === 'CANCELLED') return 'Cancelled';
  if (['COMPLETED', 'APPROVED'].includes(job.status)) return 'Complete';
  if (job.status === 'REVIEW_REQUIRED' || job.status === 'POINTER_RECOVERY_REQUIRED') return 'Blocked';
  if (['FAILED', 'REJECTED'].includes(job.status)) return 'Failed';
  return job.status.replace(/_/g, ' ').toLowerCase().replace(/^./, (character) => character.toUpperCase());
};

const lifecycleStatusClass = (job?: LifecycleJob) => {
  const label = lifecycleStatusLabel(job);
  if (label === 'Complete') return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  if (label === 'Running' || label === 'Pending') return 'border-blue-200 bg-blue-50 text-blue-700';
  if (label === 'Stopping') return 'border-amber-200 bg-amber-50 text-amber-800';
  if (label === 'Cancelled') return 'border-slate-200 bg-slate-100 text-slate-600';
  if (label === 'Blocked') return 'border-amber-200 bg-amber-50 text-amber-800';
  if (label === 'Failed') return 'border-red-200 bg-red-50 text-red-700';
  return 'border-slate-200 bg-slate-50 text-slate-600';
};

const measuredLifecycleCount = (job?: LifecycleJob) => {
  if (!job) return null;
  const candidates = [
    job.progress.current,
    job.result.pages_scanned,
    job.result.pages_crawled,
    job.result.pointer_count,
    job.result.render_count,
    job.result.finding_count,
  ];
  const value = candidates.find((candidate) => typeof candidate === 'number' && candidate > 0);
  return typeof value === 'number' ? value : null;
};

const lifecycleEvidenceSummary = (job?: LifecycleJob) => {
  if (!job) return 'No evidence has been recorded for this stage.';
  const count = measuredLifecycleCount(job);
  const phase = job.phase && job.phase !== 'pending' ? job.phase.replace(/_/g, ' ') : '';
  if (count != null && phase) return `${count.toLocaleString()} measured items · ${phase}`;
  if (count != null) return `${count.toLocaleString()} measured items recorded`;
  if (phase) return phase;
  if (job.evidence_root) return 'Evidence artifact recorded';
  return 'No measured result is available.';
};

const StatusBadge: React.FC<{ status?: string; active?: boolean }> = ({ status, active }) => {
  if (status === 'cancel_requested') {
    return <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-800">Stopping</span>;
  }
  if (status === 'cancelled') {
    return <span className="rounded-full border border-slate-200 bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-600">Cancelled</span>;
  }
  if (active || status === 'running' || status === 'pending') {
    return <span className="rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700">Crawl Running</span>;
  }
  if (status === 'completed') {
    return <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">Audit Ready</span>;
  }
  if (!status || status === 'never_crawled') {
    return <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-bold text-slate-600">Not Crawled</span>;
  }
  return <span className="rounded-full border border-red-200 bg-red-50 px-2.5 py-1 text-xs font-bold text-red-700">Crawl Failed</span>;
};

const MetricCard: React.FC<{ label: string; value: React.ReactNode; detail?: string }> = ({ label, value, detail }) => (
  <div className="min-w-0 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
    <p className="text-xs font-bold uppercase tracking-[0.08em] text-slate-500">{label}</p>
    <p className="mt-1 truncate text-2xl font-extrabold text-slate-950">{value}</p>
    {detail && <p className="mt-1 truncate text-xs text-slate-500">{detail}</p>}
  </div>
);

const EmptyPanel: React.FC<{ title: string; detail: string }> = ({ title, detail }) => (
  <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-5 py-10 text-center">
    <Circle className="mx-auto h-7 w-7 text-slate-300" />
    <p className="mt-3 font-bold text-slate-700">{title}</p>
    <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">{detail}</p>
  </div>
);

const Projects: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [crawlJobs, setCrawlJobs] = useState<CrawlJob[]>([]);
  const [lifecycleJobs, setLifecycleJobs] = useState<Record<string, LifecycleJob[]>>({});
  const [preflightReports, setPreflightReports] = useState<Record<string, PreflightReport>>({});
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [activeTab, setActiveTab] = useState<ProjectTab>('overview');
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<ProjectStatusFilter>('all');
  const [showAddModal, setShowAddModal] = useState(false);
  const [openMenuProjectId, setOpenMenuProjectId] = useState('');
  const [newProject, setNewProject] = useState({ client_name: '', domain: '', ga4_property_id: '' });
  const [includeAdminSections, setIncludeAdminSections] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [startingCrawlProjectId, setStartingCrawlProjectId] = useState('');
  const [startingAuditProjectId, setStartingAuditProjectId] = useState('');
  const [stoppingCrawlJobId, setStoppingCrawlJobId] = useState('');
  const [stoppingLifecycleJobId, setStoppingLifecycleJobId] = useState('');
  const [runningPreflightProjectId, setRunningPreflightProjectId] = useState('');
  const [startingLifecycleKey, setStartingLifecycleKey] = useState('');
  const [decidingReviewItemId, setDecidingReviewItemId] = useState('');
  const [decidingPointerTargetId, setDecidingPointerTargetId] = useState('');
  const [error, setError] = useState('');

  const loadLifecycles = useCallback(async (projectList: Project[]) => {
    const entries = await Promise.all(projectList.map(async (project) => {
      try {
        return [project.id, await api.listLifecycleJobs(project.id)] as const;
      } catch {
        return [project.id, []] as const;
      }
    }));
    const nextJobs = Object.fromEntries(entries) as Record<string, LifecycleJob[]>;
    setLifecycleJobs(nextJobs);
    return nextJobs;
  }, []);

  const loadProjects = useCallback(async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    setError('');
    try {
      const [projectList, nextCrawlJobs] = await Promise.all([
        api.listProjects(),
        api.listCrawlJobs().catch(() => []),
      ]);
      const nextLifecycleJobs = await loadLifecycles(projectList);
      setProjects(projectList);
      setCrawlJobs(nextCrawlJobs);
      setSelectedProjectId((current) => {
        if (current && projectList.some((project) => project.id === current)) return current;
        const firstActive = projectList.find((project) => (
          ACTIVE_CRAWL_STATUSES.has(project.latest_crawl_status || '')
          || (nextLifecycleJobs[project.id] || []).some((job) => ACTIVE_LIFECYCLE_STATUSES.has(job.status))
        ));
        return firstActive?.id || projectList[0]?.id || '';
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    } finally {
      if (showLoading) setIsLoading(false);
    }
  }, [loadLifecycles]);

  useEffect(() => { loadProjects(); }, [loadProjects]);

  const hasActiveWork = projects.some((project) => ACTIVE_CRAWL_STATUSES.has(project.latest_crawl_status || ''))
    || Object.values(lifecycleJobs).some((jobs) => jobs.some((job) => ACTIVE_LIFECYCLE_STATUSES.has(job.status)));

  useEffect(() => {
    if (!hasActiveWork) return;
    const timer = window.setInterval(() => loadProjects(false), 3000);
    return () => window.clearInterval(timer);
  }, [hasActiveWork, loadProjects]);

  useEffect(() => {
    if (!selectedProjectId || preflightReports[selectedProjectId]) return;
    let cancelled = false;
    api.getProjectPreflight(selectedProjectId)
      .then((report) => {
        if (!cancelled) setPreflightReports((current) => ({ ...current, [selectedProjectId]: report }));
      })
      .catch(() => {
        if (!cancelled) setPreflightReports((current) => ({ ...current, [selectedProjectId]: { status: 'not_run' } }));
      });
    return () => { cancelled = true; };
  }, [preflightReports, selectedProjectId]);

  const isProjectActive = useCallback((project: Project) => (
    ACTIVE_CRAWL_STATUSES.has(project.latest_crawl_status || '')
    || (lifecycleJobs[project.id] || []).some((job) => ACTIVE_LIFECYCLE_STATUSES.has(job.status))
    || startingCrawlProjectId === project.id
    || startingAuditProjectId === project.id
  ), [lifecycleJobs, startingAuditProjectId, startingCrawlProjectId]);

  const activeJobCount = useMemo(
    () => crawlJobs.filter((job) => ACTIVE_CRAWL_STATUSES.has(job.status)).length
      + Object.values(lifecycleJobs).flat().filter((job) => ACTIVE_LIFECYCLE_STATUSES.has(job.status)).length,
    [crawlJobs, lifecycleJobs]
  );

  const visibleProjects = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    return [...projects]
      .filter((project) => {
        const matchesSearch = !normalizedSearch
          || project.name.toLowerCase().includes(normalizedSearch)
          || project.domain.toLowerCase().includes(normalizedSearch);
        if (!matchesSearch) return false;
        if (statusFilter === 'active') return isProjectActive(project);
        if (statusFilter === 'ready') return project.latest_crawl_status === 'completed';
        if (statusFilter === 'not-run') return !project.latest_crawl_status || project.latest_crawl_status === 'never_crawled';
        if (statusFilter === 'failed') {
          return !!project.latest_crawl_status
            && !['never_crawled', 'pending', 'running', 'completed'].includes(project.latest_crawl_status);
        }
        return true;
      })
      .sort((left, right) => {
        const activeDifference = Number(isProjectActive(right)) - Number(isProjectActive(left));
        if (activeDifference !== 0) return activeDifference;
        const rightActivity = crawlJobs.find((job) => job.project_id === right.id)?.start_time || right.created_at;
        const leftActivity = crawlJobs.find((job) => job.project_id === left.id)?.start_time || left.created_at;
        const rightDate = rightActivity ? new Date(rightActivity).getTime() : 0;
        const leftDate = leftActivity ? new Date(leftActivity).getTime() : 0;
        return rightDate - leftDate;
      });
  }, [crawlJobs, isProjectActive, projects, searchTerm, statusFilter]);

  const selectedProject = projects.find((project) => project.id === selectedProjectId) || null;
  const selectedProjectLifecycleJobs = selectedProject ? lifecycleJobs[selectedProject.id] || [] : [];
  const selectedProjectCrawlJobs = useMemo(
    () => selectedProject ? crawlJobs.filter((job) => job.project_id === selectedProject.id) : [],
    [crawlJobs, selectedProject]
  );

  useEffect(() => {
    if (!selectedProject?.domain) return;
    const latestCrawlJob = selectedProjectCrawlJobs[0];
    setActiveOrbProjectContext({
      project_id: String(selectedProject.id),
      canonical_domain: selectedProject.domain,
      canonical_base_url: canonicalOrbBaseUrl(selectedProject.domain),
      selected_crawl_job_id: latestCrawlJob?.id || selectedProject.latest_crawl_id || null,
      active_customer_route: '/',
    });
  }, [selectedProject, selectedProjectCrawlJobs]);

  const handleSelectProject = (projectId: string) => {
    setSelectedProjectId(projectId);
    setActiveTab('overview');
    setOpenMenuProjectId('');
    if (window.innerWidth < 768) {
      window.setTimeout(() => document.getElementById('selected-project-workspace')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0);
    }
  };

  const handleAddProject = async () => {
    if (!newProject.client_name.trim() || !newProject.domain.trim()) return;
    setError('');
    setIsCreatingProject(true);
    try {
      const created = await api.createProject({
        name: newProject.client_name.trim(),
        domain: newProject.domain.trim().replace(/^https?:\/\//, '').replace(/\/$/, ''),
        ga4_property_id: newProject.ga4_property_id.trim() || null,
      });
      setShowAddModal(false);
      setNewProject({ client_name: '', domain: '', ga4_property_id: '' });
      await loadProjects();
      setSelectedProjectId(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add project');
    } finally {
      setIsCreatingProject(false);
    }
  };

  const handleDelete = async (id: string) => {
    setError('');
    try {
      await api.deleteProject(id);
      setOpenMenuProjectId('');
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete project');
    }
  };

  const handleCrawl = async (projectId: string, recrawl = false) => {
    setError('');
    setStartingCrawlProjectId(projectId);
    try {
      const config = {
        max_pages: 500,
        delay: 1.5,
        max_depth: 8,
        seed_urls: WEBSITE_CONTEXT_SEED_URLS,
        include_admin_sections: includeAdminSections,
      };
      const crawl = recrawl ? await api.recrawlProject(projectId, config) : await api.startCrawl(projectId, config);
      navigate(`/crawl/${crawl.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start crawl');
      setStartingCrawlProjectId('');
    }
  };

  const handleStopCrawl = async (crawlJobId: string) => {
    setError('');
    setStoppingCrawlJobId(crawlJobId);
    try {
      await api.cancelCrawlJob(crawlJobId);
      await loadProjects(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop crawl');
    } finally {
      setStoppingCrawlJobId('');
    }
  };

  const handleReaudit = async (projectId: string) => {
    setError('');
    setStartingAuditProjectId(projectId);
    try {
      const audit = await api.reauditProject(projectId);
      navigate(`/audit/${audit.audit_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run audit');
      setStartingAuditProjectId('');
    }
  };

  const handlePreflight = async (projectId: string) => {
    setError('');
    setRunningPreflightProjectId(projectId);
    try {
      const report = await api.runProjectPreflight(projectId);
      setPreflightReports((current) => ({ ...current, [projectId]: report }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run preflight scan');
    } finally {
      setRunningPreflightProjectId('');
    }
  };

  const handleStartLifecycle = async (projectId: string, jobType: LifecycleJobType) => {
    const key = `${projectId}:${jobType}`;
    setError('');
    setStartingLifecycleKey(key);
    try {
      await api.startLifecycleJob(projectId, jobType, jobType === 'MAP_CRAWL' ? {
        max_pages: 500,
        delay: 1.5,
        max_depth: 8,
        seed_urls: WEBSITE_CONTEXT_SEED_URLS,
        include_admin_sections: includeAdminSections,
      } : {});
      await loadProjects(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to start ${jobType}`);
    } finally {
      setStartingLifecycleKey('');
    }
  };

  const handleStopLifecycle = async (jobId: string) => {
    setError('');
    setStoppingLifecycleJobId(jobId);
    try {
      await api.cancelLifecycleJob(jobId);
      await loadProjects(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop lifecycle scan');
    } finally {
      setStoppingLifecycleJobId('');
    }
  };

  const handleReviewDecision = async (jobId: string, itemId: string, decision: 'approve' | 'reject') => {
    setError('');
    setDecidingReviewItemId(itemId);
    try {
      await api.decideLifecycleReviewItem(jobId, itemId, decision);
      await loadProjects(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record review decision');
    } finally {
      setDecidingReviewItemId('');
    }
  };

  const handlePointerAuthority = async (jobId: string, targetId: string, decision: 'approve' | 'reject') => {
    setError('');
    setDecidingPointerTargetId(targetId);
    try {
      await api.decidePointerAuthority(jobId, targetId, decision);
      await loadProjects(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record pointer authority');
    } finally {
      setDecidingPointerTargetId('');
    }
  };

  const renderSelectedWorkspace = () => {
    if (!selectedProject) {
      return <EmptyPanel title="Select a project" detail="Choose a project from the navigator to open its operations workspace." />;
    }

    const isCrawlActive = ACTIVE_CRAWL_STATUSES.has(selectedProject.latest_crawl_status || '');
    const isStartingCrawl = startingCrawlProjectId === selectedProject.id;
    const isStartingAudit = startingAuditProjectId === selectedProject.id;
    const preflight = preflightReports[selectedProject.id];
    const detected = preflight?.detected || {};
    const latestLifecycleByType = Object.fromEntries(
      LIFECYCLE_STAGES.map((stage) => [stage.type, selectedProjectLifecycleJobs.find((job) => job.job_type === stage.type)])
    ) as Partial<Record<LifecycleJobType, LifecycleJob>>;
    const completedLifecycleStages = LIFECYCLE_STAGES.filter((stage) =>
      ['COMPLETED', 'APPROVED'].includes(latestLifecycleByType[stage.type]?.status || '')
    ).length;
    const activeLifecycleJob = selectedProjectLifecycleJobs.find((job) => ACTIVE_LIFECYCLE_STATUSES.has(job.status));
    const latestCrawlJob = selectedProjectCrawlJobs[0];
    const isStoppingCrawl = !!latestCrawlJob && (stoppingCrawlJobId === latestCrawlJob.id || latestCrawlJob.status === 'cancel_requested');
    const orbScanJob = latestLifecycleByType.ORB_SCAN;
    const pointerRecoveryJob = latestLifecycleByType.POINTER_RECOVERY;
    const initialQuality = (orbScanJob?.result.pointer_quality || {}) as Record<string, unknown>;
    const pointerReview = pointerRecoveryJob?.review_items.find((item) => (
      item.status === 'open' && ['pointer_owner_verification', 'pointer_recovery_visual_review'].includes(item.category)
    ));
    const pointerReviewDetails = (pointerReview?.details || {}) as Record<string, unknown>;
    const pointerDecisions = (pointerReviewDetails.pointer_decisions || {}) as Record<string, unknown>;
    const reviewPointers = (Array.isArray(pointerReviewDetails.pointers) ? pointerReviewDetails.pointers : []) as Array<Record<string, unknown>>;
    const unresolvedPointers = reviewPointers.filter((pointer) => !pointerDecisions[String(pointer.target_id || '')]);
    const stateSentence = activeLifecycleJob
      ? `${LIFECYCLE_STAGES.find((stage) => stage.type === activeLifecycleJob.job_type)?.label || activeLifecycleJob.job_type} is ${activeLifecycleJob.status.toLowerCase()}.`
      : isCrawlActive
        ? `${selectedProject.latest_pages_crawled || 0} pages have been processed in the active crawl.`
        : selectedProject.latest_crawl_status === 'completed'
          ? 'The latest crawl is complete and ready for audit, reporting, or another scan.'
          : 'This project is ready for its first website crawl.';

    const overviewContent = (
      <div className="grid gap-5 xl:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-slate-500">Current crawl</p>
              <h3 className="mt-1 text-lg font-bold text-slate-950">{latestCrawlJob ? `Job #${latestCrawlJob.id}` : 'No crawl job'}</h3>
            </div>
                <StatusBadge status={latestCrawlJob?.status || selectedProject.latest_crawl_status} active={isCrawlActive || isStartingCrawl} />
          </div>
          {latestCrawlJob ? (
            <dl className="mt-5 grid grid-cols-2 gap-4 text-sm">
              <div><dt className="text-slate-500">Pages processed</dt><dd className="mt-1 font-bold text-slate-900">{latestCrawlJob.pages_crawled ?? selectedProject.latest_pages_crawled ?? 0}</dd></div>
              <div><dt className="text-slate-500">Pages found</dt><dd className="mt-1 font-bold text-slate-900">{latestCrawlJob.pages_found ?? 'Unavailable'}</dd></div>
              <div><dt className="text-slate-500">Started</dt><dd className="mt-1 font-bold text-slate-900">{formatDateTime(latestCrawlJob.start_time)}</dd></div>
              <div><dt className="text-slate-500">Elapsed</dt><dd className="mt-1 font-bold text-slate-900">{formatElapsed(latestCrawlJob.start_time, latestCrawlJob.end_time)}</dd></div>
            </dl>
          ) : <p className="mt-4 text-sm text-slate-500">No crawl history is available for this project.</p>}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.1em] text-slate-500">Audit and report state</p>
          <div className="mt-4 divide-y divide-slate-200">
            <div className="flex items-center justify-between gap-4 py-3 first:pt-0">
              <span className="text-sm text-slate-600">Latest audit</span>
              <span className="text-sm font-bold text-slate-900">{selectedProject.latest_audit_id ? `Report #${selectedProject.latest_audit_id}` : 'Not run'}</span>
            </div>
            <div className="flex items-center justify-between gap-4 py-3">
              <span className="text-sm text-slate-600">Audit score</span>
              <span className="text-sm font-bold text-slate-900">{selectedProject.latest_audit_score == null ? 'Unavailable' : Math.round(selectedProject.latest_audit_score)}</span>
            </div>
            <div className="flex items-center justify-between gap-4 py-3 last:pb-0">
              <span className="text-sm text-slate-600">Report state</span>
              <span className="text-sm font-bold text-slate-900">{selectedProject.latest_audit_id ? 'Available' : 'Not generated'}</span>
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm xl:col-span-2">
          <p className="text-xs font-bold uppercase tracking-[0.1em] text-slate-500">Recent activity and evidence</p>
          {selectedProjectLifecycleJobs.length > 0 ? (
            <div className="mt-4 divide-y divide-slate-200">
              {selectedProjectLifecycleJobs.slice(0, 5).map((job) => (
                <div key={job.id} className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-bold text-slate-900">{LIFECYCLE_STAGES.find((stage) => stage.type === job.job_type)?.label || job.job_type.replace(/_/g, ' ')}</p>
                    <p className="text-xs text-slate-500">{lifecycleEvidenceSummary(job)}</p>
                  </div>
                  <span className={`w-fit rounded-full border px-2.5 py-1 text-xs font-bold ${lifecycleStatusClass(job)}`}>{lifecycleStatusLabel(job)}</span>
                </div>
              ))}
            </div>
          ) : <p className="mt-4 text-sm text-slate-500">No lifecycle evidence has been recorded.</p>}
        </section>
      </div>
    );

    const lifecycleContent = (
      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-slate-200 bg-slate-50 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="font-bold text-slate-950">Five-stage lifecycle</h3>
            <p className="text-sm text-slate-500">Measured evidence and approval gates, in order.</p>
          </div>
          <label className="flex items-center gap-2 text-xs font-semibold text-slate-700">
            <input type="checkbox" checked={includeAdminSections} onChange={(event) => setIncludeAdminSections(event.target.checked)} className="rounded border-slate-300 text-brand-accent focus:ring-brand-accent" />
            Include admin routes in Map Crawl
          </label>
        </div>
        <ol className="divide-y divide-slate-200">
          {LIFECYCLE_STAGES.map((stage, index) => {
            const job = latestLifecycleByType[stage.type];
            const isStarting = startingLifecycleKey === `${selectedProject.id}:${stage.type}`;
            const isActive = !!job && ACTIVE_LIFECYCLE_STATUSES.has(job.status);
            const isStopping = !!job && (stoppingLifecycleJobId === job.id || job.status === 'CANCEL_REQUESTED');
            const mapApproved = latestLifecycleByType.MAP_CRAWL?.status === 'APPROVED';
            const siteComplete = ['COMPLETED', 'APPROVED'].includes(latestLifecycleByType.SITE_SCAN?.status || '');
            const orbComplete = ['COMPLETED', 'APPROVED'].includes(latestLifecycleByType.ORB_SCAN?.status || '');
            const recoveryRequired = latestLifecycleByType.ORB_SCAN?.status === 'POINTER_RECOVERY_REQUIRED';
            const recoveryComplete = ['COMPLETED', 'APPROVED'].includes(latestLifecycleByType.POINTER_RECOVERY?.status || '');
            const dependencyReady = stage.type === 'MAP_CRAWL'
              || (stage.type === 'SITE_SCAN' && mapApproved)
              || (stage.type === 'ORB_SCAN' && siteComplete)
              || (stage.type === 'POINTER_RECOVERY' && recoveryRequired)
              || (stage.type === 'FULL_AUDIT' && (orbComplete || recoveryComplete));
            const openReview = job?.review_items.find((item) => item.status === 'open' && !['pointer_recovery_visual_review', 'pointer_owner_verification'].includes(item.category));
            return (
              <li key={stage.type} className="grid gap-4 px-5 py-5 md:grid-cols-[48px_minmax(0,1fr)_auto] md:items-center">
                <div className={`flex h-10 w-10 items-center justify-center rounded-full border-2 text-sm font-extrabold ${job && ['COMPLETED', 'APPROVED'].includes(job.status) ? 'border-emerald-500 bg-emerald-50 text-emerald-700' : job && ACTIVE_LIFECYCLE_STATUSES.has(job.status) ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-slate-300 bg-white text-slate-500'}`}>
                  {job && ['COMPLETED', 'APPROVED'].includes(job.status) ? <CheckCircle2 className="h-5 w-5" /> : index + 1}
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h4 className="font-bold text-slate-950">{stage.label}</h4>
                    <span className={`rounded-full border px-2.5 py-1 text-xs font-bold ${lifecycleStatusClass(job)}`}>{lifecycleStatusLabel(job)}</span>
                    {measuredLifecycleCount(job) != null && <span className="text-xs font-semibold text-slate-500">{measuredLifecycleCount(job)?.toLocaleString()} items</span>}
                  </div>
                  <p className="mt-1 text-sm text-slate-500">{lifecycleEvidenceSummary(job)}</p>
                  {openReview && (
                    <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
                      <p className="text-xs font-bold text-amber-900">{openReview.title}</p>
                      <div className="mt-2 flex gap-2">
                        <button onClick={() => handleReviewDecision(job!.id, openReview.id, 'approve')} disabled={decidingReviewItemId === openReview.id} className="rounded-md bg-emerald-100 px-2.5 py-1.5 text-xs font-bold text-emerald-700 disabled:opacity-50">Approve</button>
                        <button onClick={() => handleReviewDecision(job!.id, openReview.id, 'reject')} disabled={decidingReviewItemId === openReview.id} className="rounded-md bg-red-100 px-2.5 py-1.5 text-xs font-bold text-red-700 disabled:opacity-50">Reject</button>
                      </div>
                    </div>
                  )}
                </div>
                {isActive ? (
                  <button
                    onClick={() => job && handleStopLifecycle(job.id)}
                    disabled={isStopping}
                    className="inline-flex items-center justify-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-bold text-red-700 hover:bg-red-100 disabled:opacity-50"
                  >
                    {isStopping ? <Activity className="h-4 w-4 animate-pulse" /> : <Square className="h-4 w-4 fill-current" />}
                    {isStopping ? 'Stopping…' : 'Stop'}
                  </button>
                ) : !stage.automatic && (
                  <button
                    onClick={() => handleStartLifecycle(selectedProject.id, stage.type)}
                    disabled={isStarting || !dependencyReady || job?.status === 'REVIEW_REQUIRED'}
                    className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {isStarting ? 'Starting…' : job ? 'Run again' : 'Run'}
                  </button>
                )}
              </li>
            );
          })}
        </ol>
      </section>
    );

    const preflightHasReport = !!preflight && preflight.status !== 'not_run' && preflight.pages_scanned != null;
    const preflightContent = (
      <div className="space-y-5">
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-50 text-brand-accent"><ShieldCheck className="h-5 w-5" /></div>
              <div>
                <h3 className="font-bold text-slate-950">Deployment preflight</h3>
                <p className="text-sm text-slate-500">Supporting readiness scan, separate from the lifecycle.</p>
              </div>
            </div>
            <button onClick={() => handlePreflight(selectedProject.id)} disabled={runningPreflightProjectId === selectedProject.id} className="rounded-lg bg-brand-dark px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-accent disabled:opacity-50">
              {runningPreflightProjectId === selectedProject.id ? 'Running…' : preflightHasReport ? 'Re-run preflight' : 'Run preflight'}
            </button>
          </div>
        </section>
        {preflightHasReport ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="Confidence" value={formatConfidence(preflight)} />
            <MetricCard label="Pages scanned" value={preflight.pages_scanned ?? '—'} />
            <MetricCard label="Sitemap" value={detected.sitemap_xml ? 'Present' : 'Missing'} />
            <MetricCard label="Robots.txt" value={detected.robots_txt ? 'Present' : 'Missing'} />
            <MetricCard label="Authentication" value={detected.has_auth_pages ? 'Detected' : 'Not detected'} />
            <MetricCard label="Products" value={detected.has_products ? 'Detected' : 'Not detected'} />
            <MetricCard label="Warnings" value={preflight.warnings?.length || 0} />
            <MetricCard label="Install mode" value={preflight.recommended_install_mode || 'Unavailable'} />
          </div>
        ) : <EmptyPanel title="Preflight not run" detail="Run preflight to collect public readiness, installation, and detection evidence." />}
      </div>
    );

    const pointerContent = (
      <div className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Initial pointers" value={String(orbScanJob?.result.pointer_count ?? 'Not run')} detail="Initial extraction" />
          <MetricCard label="Initially safe" value={String(initialQuality.stable_count ?? 'Not run')} detail="Initial extraction" />
          <MetricCard label="Stable ratio" value={typeof initialQuality.stable_ratio === 'number' ? `${Math.round(initialQuality.stable_ratio * 100)}%` : 'Not run'} detail="Initial extraction" />
          <MetricCard label="Needs review" value={String(pointerRecoveryJob ? (pointerRecoveryJob.result.unresolved_pointer_count ?? unresolvedPointers.length) : 'Not run')} detail="Runtime recovery" />
        </div>
        <div className="grid gap-5 xl:grid-cols-2">
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-slate-500">Initial extraction</p>
            {orbScanJob ? (
              <dl className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between gap-4"><dt className="text-slate-500">Status</dt><dd className="font-bold text-slate-900">{lifecycleStatusLabel(orbScanJob)}</dd></div>
                <div className="flex justify-between gap-4"><dt className="text-slate-500">Pointers extracted</dt><dd className="font-bold text-slate-900">{String(orbScanJob.result.pointer_count ?? 'Unavailable')}</dd></div>
                <div className="flex justify-between gap-4"><dt className="text-slate-500">Evidence time</dt><dd className="font-bold text-slate-900">{formatDateTime(orbScanJob.end_time || orbScanJob.start_time)}</dd></div>
              </dl>
            ) : <p className="mt-4 text-sm text-slate-500">ORB Scan has not produced an initial pointer artifact.</p>}
          </section>
          <section className="rounded-xl border border-violet-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-violet-600">Runtime recovery</p>
            {pointerRecoveryJob ? (
              <dl className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between gap-4"><dt className="text-slate-500">Recovery status</dt><dd className="font-bold text-slate-900">{lifecycleStatusLabel(pointerRecoveryJob)}</dd></div>
                <div className="flex justify-between gap-4"><dt className="text-slate-500">Recovery-pass count</dt><dd className="font-bold text-slate-900">{String(pointerRecoveryJob.result.automatic_attempt ?? pointerRecoveryJob.config.automatic_attempt ?? 1)}</dd></div>
                <div className="flex justify-between gap-4"><dt className="text-slate-500">Latest verification</dt><dd className="font-bold text-slate-900">{formatDateTime(pointerRecoveryJob.end_time || pointerRecoveryJob.start_time)}</dd></div>
              </dl>
            ) : <p className="mt-4 text-sm text-slate-500">No runtime recovery pass has been recorded.</p>}
          </section>
        </div>
        {pointerRecoveryJob && unresolvedPointers.length > 0 && (
          <section className="rounded-xl border border-amber-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2"><AlertTriangle className="h-5 w-5 text-amber-600" /><h3 className="font-bold text-slate-950">Owner pointer review</h3></div>
            <div className="mt-4 divide-y divide-slate-200">
              {unresolvedPointers.slice(0, 8).map((pointer) => {
                const targetId = String(pointer.target_id || '');
                const rawRoute = String(pointer.page_route || '/');
                const reviewUrl = /^https?:\/\//.test(rawRoute) ? rawRoute : `https://${selectedProject.domain}${rawRoute.startsWith('/') ? rawRoute : `/${rawRoute}`}`;
                return (
                  <div key={targetId} className="py-4 first:pt-0 last:pb-0">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-bold text-slate-900">{String(pointer.meaning || targetId)}</p>
                        <p className="truncate text-xs text-slate-500">{rawRoute} · {String(pointer.semantic_locator || 'No locator')}</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <a href={reviewUrl} target="_blank" rel="noreferrer" className="rounded-md border border-slate-300 px-2.5 py-1.5 text-xs font-bold text-slate-700">Inspect</a>
                        <button onClick={() => handlePointerAuthority(pointerRecoveryJob.id, targetId, 'approve')} disabled={decidingPointerTargetId === targetId} className="rounded-md bg-emerald-100 px-2.5 py-1.5 text-xs font-bold text-emerald-700 disabled:opacity-50">Owner verify</button>
                        <button onClick={() => handlePointerAuthority(pointerRecoveryJob.id, targetId, 'reject')} disabled={decidingPointerTargetId === targetId} className="rounded-md bg-red-100 px-2.5 py-1.5 text-xs font-bold text-red-700 disabled:opacity-50">Reject</button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </div>
    );

    const jobsContent = selectedProjectCrawlJobs.length > 0 ? (
      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 bg-slate-50 px-5 py-4">
          <h3 className="font-bold text-slate-950">Crawl and audit jobs</h3>
          <p className="text-sm text-slate-500">Current work first, followed by available crawl history.</p>
        </div>
        <div className="divide-y divide-slate-200">
          {selectedProjectCrawlJobs.map((job, index) => (
            <div key={job.id} className="grid gap-4 px-5 py-5 lg:grid-cols-[minmax(0,1fr)_repeat(4,minmax(90px,auto))] lg:items-center">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-bold text-slate-950">Crawl #{job.id}</p>
                  {index === 0 && <span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-slate-600">Latest</span>}
                </div>
                <p className="mt-1 text-xs text-slate-500">Started {formatDateTime(job.start_time)}</p>
              </div>
              <div><p className="text-xs text-slate-500">Status</p><p className="mt-1 text-sm font-bold capitalize text-slate-900">{job.status}</p></div>
              <div><p className="text-xs text-slate-500">Pages</p><p className="mt-1 text-sm font-bold text-slate-900">{job.pages_crawled ?? 0}</p></div>
              <div><p className="text-xs text-slate-500">Elapsed</p><p className="mt-1 text-sm font-bold text-slate-900">{formatElapsed(job.start_time, job.end_time)}</p></div>
              {ACTIVE_CRAWL_STATUSES.has(job.status) ? (
                <button onClick={() => handleStopCrawl(job.id)} disabled={stoppingCrawlJobId === job.id || job.status === 'cancel_requested'} className="inline-flex items-center justify-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-bold text-red-700 hover:bg-red-100 disabled:opacity-50">
                  <Square className="h-3.5 w-3.5 fill-current" /> {job.status === 'cancel_requested' || stoppingCrawlJobId === job.id ? 'Stopping…' : 'Stop'}
                </button>
              ) : (
                <button onClick={() => navigate(`/crawl/${job.id}`)} className="inline-flex items-center justify-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50">View <ChevronRight className="h-4 w-4" /></button>
              )}
            </div>
          ))}
        </div>
      </section>
    ) : <EmptyPanel title="No jobs available" detail="Start a crawl to create the first job record for this project." />;

    const tabContent: Record<ProjectTab, React.ReactNode> = {
      overview: overviewContent,
      lifecycle: lifecycleContent,
      preflight: preflightContent,
      pointer: pointerContent,
      jobs: jobsContent,
    };

    return (
      <div id="selected-project-workspace" className="min-w-0 scroll-mt-24">
        <div className="border-b border-slate-200 bg-white px-5 py-5 sm:px-6">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="truncate text-2xl font-extrabold tracking-tight text-slate-950">{selectedProject.name}</h2>
                <StatusBadge status={selectedProject.latest_crawl_status} active={isCrawlActive || isStartingCrawl} />
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-500">
                <span className="truncate">{selectedProject.domain}</span>
                <a href={`https://${selectedProject.domain}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-brand-accent hover:text-brand-dark">Visit site <ExternalLink className="h-3.5 w-3.5" /></a>
              </div>
              <p className="mt-3 text-sm text-slate-600">{stateSentence}</p>
            </div>
            <div className="relative">
              <button onClick={() => setOpenMenuProjectId(openMenuProjectId === selectedProject.id ? '' : selectedProject.id)} className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" aria-label="Project actions"><MoreVertical className="h-5 w-5" /></button>
              {openMenuProjectId === selectedProject.id && (
                <div className="absolute right-0 top-11 z-20 w-48 rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl">
                  <button onClick={() => handleDelete(selectedProject.id)} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-semibold text-red-700 hover:bg-red-50"><Trash2 className="h-4 w-4" /> Delete project</button>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="border-b border-slate-200 bg-slate-50 px-5 py-5 sm:px-6">
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
            <MetricCard label="Pages crawled" value={selectedProject.latest_pages_crawled ?? '—'} />
            <MetricCard label="Audit score" value={selectedProject.latest_audit_score == null ? '—' : Math.round(selectedProject.latest_audit_score)} />
            <MetricCard label="Lifecycle" value={`${completedLifecycleStages}/${LIFECYCLE_STAGES.length}`} detail="stages complete" />
            <MetricCard label="Preflight" value={formatConfidence(preflight)} detail="confidence" />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {isCrawlActive && latestCrawlJob ? (
              <button onClick={() => handleStopCrawl(latestCrawlJob.id)} disabled={isStoppingCrawl} className="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-bold text-red-700 hover:bg-red-100 disabled:opacity-50">
                {isStoppingCrawl ? <Activity className="h-4 w-4 animate-pulse" /> : <Square className="h-4 w-4 fill-current" />}
                {isStoppingCrawl ? 'Stopping crawl…' : 'Stop crawl'}
              </button>
            ) : (
              <button onClick={() => handleCrawl(selectedProject.id, !!selectedProject.latest_crawl_id)} disabled={isStartingCrawl} className="inline-flex items-center gap-2 rounded-lg bg-brand-dark px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-accent disabled:opacity-50">
                {isStartingCrawl ? <Activity className="h-4 w-4 animate-pulse" /> : selectedProject.latest_crawl_id ? <RotateCw className="h-4 w-4" /> : <Globe className="h-4 w-4" />}
                {isStartingCrawl ? 'Starting…' : selectedProject.latest_crawl_id ? 'Re-crawl' : 'Start crawl'}
              </button>
            )}
            <button onClick={() => handleReaudit(selectedProject.id)} disabled={isStartingAudit || selectedProject.latest_crawl_status !== 'completed'} className="inline-flex items-center gap-2 rounded-lg border border-violet-200 bg-violet-50 px-4 py-2.5 text-sm font-bold text-violet-700 hover:bg-violet-100 disabled:opacity-40">
              {isStartingAudit ? <Activity className="h-4 w-4 animate-pulse" /> : <ShieldCheck className="h-4 w-4" />}
              {isStartingAudit ? 'Starting…' : selectedProject.latest_audit_id ? 'Re-audit' : 'Run audit'}
            </button>
            <button onClick={() => navigate(`/reports/${selectedProject.id}`)} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50"><FileText className="h-4 w-4" /> Reports</button>
            {selectedProject.ga4_property_id && <button onClick={() => navigate(`/ga4/${selectedProject.ga4_property_id}`)} className="inline-flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2.5 text-sm font-bold text-blue-700 hover:bg-blue-100"><BarChart3 className="h-4 w-4" /> GA4</button>}
          </div>
        </div>

        <div className="overflow-x-auto border-b border-slate-200 bg-white px-5 sm:px-6">
          <div className="flex min-w-max gap-6">
            {PROJECT_TABS.map((tab) => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`border-b-2 py-4 text-sm font-bold transition-colors ${activeTab === tab.id ? 'border-brand-accent text-brand-accent' : 'border-transparent text-slate-500 hover:text-slate-900'}`}>{tab.label}</button>
            ))}
          </div>
        </div>
        <div className="bg-slate-100 p-4 sm:p-6">{tabContent[activeTab]}</div>
      </div>
    );
  };

  return (
    <div className="space-y-5">
      <header className="rounded-2xl border border-slate-200 bg-white px-5 py-5 shadow-sm sm:px-6">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-950">Client Projects</h1>
            <p className="mt-1 text-sm text-slate-500">{projects.length} {projects.length === 1 ? 'project' : 'projects'} · {activeJobCount} active {activeJobCount === 1 ? 'job' : 'jobs'}</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <label className="relative min-w-0 sm:w-64">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Search projects" className="w-full rounded-lg border border-slate-300 bg-white py-2.5 pl-9 pr-3 text-sm focus:border-brand-accent focus:outline-none focus:ring-2 focus:ring-brand-orange/20" />
            </label>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as ProjectStatusFilter)} className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-semibold text-slate-700 focus:border-brand-accent focus:outline-none">
              <option value="all">All statuses</option>
              <option value="active">Active</option>
              <option value="ready">Audit ready</option>
              <option value="not-run">Not crawled</option>
              <option value="failed">Failed</option>
            </select>
            <button onClick={() => setShowAddModal(true)} className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand-orange px-4 py-2.5 text-sm font-bold text-brand-dark hover:bg-brand-accent hover:text-white"><FolderPlus className="h-4 w-4" /> New project</button>
          </div>
        </div>
      </header>

      {error && <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</div>}

      {isLoading ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-slate-500">Loading projects…</div>
      ) : projects.length === 0 ? (
        <EmptyPanel title="No projects yet" detail="Create a project to start its first crawl and operational workspace." />
      ) : (
        <div className="grid min-w-0 overflow-hidden rounded-2xl border border-slate-300 bg-white shadow-sm lg:grid-cols-[340px_minmax(0,1fr)]">
          <aside className="border-b border-slate-300 bg-slate-50 lg:border-b-0 lg:border-r">
            <div className="border-b border-slate-200 px-4 py-3">
              <p className="text-xs font-extrabold uppercase tracking-[0.14em] text-slate-500">Project list</p>
              <p className="mt-1 text-xs text-slate-400">Active projects appear first</p>
            </div>
            <div className="max-h-[520px] overflow-y-auto lg:max-h-[calc(100vh-235px)] lg:min-h-[620px]">
              {visibleProjects.length > 0 ? visibleProjects.map((project) => {
                const active = isProjectActive(project);
                const selected = project.id === selectedProjectId;
                return (
                  <button key={project.id} onClick={() => handleSelectProject(project.id)} className={`relative w-full border-b border-slate-200 px-4 py-4 text-left transition-colors ${selected ? 'bg-white' : 'bg-slate-50 hover:bg-white'}`}>
                    {selected && <span className="absolute inset-y-0 left-0 w-1 bg-brand-orange" />}
                    <div className="flex items-start gap-3">
                      <div className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${active ? 'bg-blue-500 shadow-[0_0_0_4px_rgba(59,130,246,0.12)]' : project.latest_crawl_status === 'completed' ? 'bg-emerald-500' : 'bg-slate-300'}`} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-2">
                          <p className={`truncate text-sm font-extrabold ${selected ? 'text-brand-dark' : 'text-slate-900'}`}>{project.name}</p>
                          {active && <Activity className="h-4 w-4 shrink-0 animate-pulse text-blue-600" />}
                        </div>
                        <p className="mt-0.5 truncate text-xs text-slate-500">{project.domain}</p>
                        <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
                          <span>{project.latest_pages_crawled ?? 0} pages</span><span>·</span>
                          <span>{project.latest_audit_score == null ? 'No score' : `Score ${Math.round(project.latest_audit_score)}`}</span>
                        </div>
                        <div className="mt-2"><StatusBadge status={project.latest_crawl_status} active={ACTIVE_CRAWL_STATUSES.has(project.latest_crawl_status || '') || startingCrawlProjectId === project.id} /></div>
                      </div>
                      <ChevronRight className={`mt-1 h-4 w-4 shrink-0 ${selected ? 'text-brand-accent' : 'text-slate-300'}`} />
                    </div>
                  </button>
                );
              }) : <div className="px-4 py-10 text-center text-sm text-slate-500">No projects match these filters.</div>}
            </div>
          </aside>
          <main className="min-w-0">{renderSelectedWorkspace()}</main>
        </div>
      )}

      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-brand-dark/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
            <div className="border-b border-slate-200 bg-slate-50 px-6 py-5">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-brand-accent">New project workspace</p>
              <h2 className="mt-1 text-2xl font-bold text-gray-900">Create new project</h2>
              <p className="mt-1 text-sm text-slate-500">Add the client identity and website. Operational controls will live in its workspace.</p>
            </div>
            <div className="space-y-4 px-6 py-5">
              {error && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
              <div><label className="mb-2 block text-sm font-bold text-gray-700">Client name</label><input value={newProject.client_name} onChange={(event) => setNewProject({ ...newProject, client_name: event.target.value })} className="w-full rounded-lg border border-gray-300 px-4 py-3 focus:border-brand-accent focus:outline-none focus:ring-2 focus:ring-brand-orange/25" placeholder="Client name" /></div>
              <div><label className="mb-2 block text-sm font-bold text-gray-700">Domain</label><input value={newProject.domain} onChange={(event) => setNewProject({ ...newProject, domain: event.target.value })} className="w-full rounded-lg border border-gray-300 px-4 py-3 focus:border-brand-accent focus:outline-none focus:ring-2 focus:ring-brand-orange/25" placeholder="domain.com" /></div>
              <div><label className="mb-2 block text-sm font-bold text-gray-700">GA4 property ID <span className="font-medium text-slate-400">(optional)</span></label><input value={newProject.ga4_property_id} onChange={(event) => setNewProject({ ...newProject, ga4_property_id: event.target.value })} className="w-full rounded-lg border border-gray-300 px-4 py-3 focus:border-brand-accent focus:outline-none focus:ring-2 focus:ring-brand-orange/25" placeholder="Property ID" /></div>
            </div>
            <div className="flex gap-3 border-t border-slate-200 bg-slate-50 px-6 py-4">
              <button onClick={() => { setShowAddModal(false); setError(''); }} disabled={isCreatingProject} className="flex-1 rounded-lg border border-gray-300 bg-white py-3 font-semibold text-slate-700 hover:bg-gray-100">Cancel</button>
              <button onClick={handleAddProject} disabled={isCreatingProject || !newProject.client_name.trim() || !newProject.domain.trim()} className="flex-1 rounded-lg bg-brand-orange py-3 font-bold text-brand-dark hover:bg-brand-accent hover:text-white disabled:opacity-50">{isCreatingProject ? 'Creating…' : 'Create project'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Projects;
