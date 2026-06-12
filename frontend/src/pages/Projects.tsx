import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Globe, Trash2, ExternalLink, BarChart3, FolderPlus, FileText, RotateCw, ShieldCheck } from 'lucide-react';
import { api, PreflightReport, Project } from '../services/api';

const ACTIVE_CRAWL_STATUSES = new Set(['pending', 'running']);
const WEBSITE_CONTEXT_SEED_URLS = [
  '/',
  '/admin',
  '/admin/customers',
  '/dashboard',
  '/account',
  '/cart',
  '/checkout',
  '/checkout/success',
  '/login',
  '/signup',
  '/privacy',
  '/terms',
  '/sitemap.xml',
  '/robots.txt'
];

const Projects: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newProject, setNewProject] = useState({ client_name: '', domain: '', ga4_property_id: '' });
  const [isLoading, setIsLoading] = useState(true);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [startingCrawlProjectId, setStartingCrawlProjectId] = useState('');
  const [startingAuditProjectId, setStartingAuditProjectId] = useState('');
  const [runningPreflightProjectId, setRunningPreflightProjectId] = useState('');
  const [expandedPreflightProjectId, setExpandedPreflightProjectId] = useState('');
  const [preflightReports, setPreflightReports] = useState<Record<string, PreflightReport>>({});
  const [error, setError] = useState('');

  const loadPreflights = useCallback(async (projectList: Project[]) => {
    const entries = await Promise.all(
      projectList.map(async (project) => {
        try {
          return [project.id, await api.getProjectPreflight(project.id)] as const;
        } catch {
          return [project.id, { status: 'not_run' }] as const;
        }
      })
    );
    setPreflightReports(Object.fromEntries(entries));
  }, []);

  const loadProjects = useCallback(async (showLoading = true) => {
    if (showLoading) {
      setIsLoading(true);
    }
    setError('');
    try {
      const projectList = await api.listProjects();
      setProjects(projectList);
      await loadPreflights(projectList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    } finally {
      if (showLoading) {
        setIsLoading(false);
      }
    }
  }, [loadPreflights]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const hasActiveCrawl = projects.some((project) => ACTIVE_CRAWL_STATUSES.has(project.latest_crawl_status || ''));

  useEffect(() => {
    if (!hasActiveCrawl) return;
    const timer = window.setInterval(() => loadProjects(false), 3000);
    return () => window.clearInterval(timer);
  }, [hasActiveCrawl, loadProjects]);

  const handleAddProject = async () => {
    if (!newProject.client_name.trim() || !newProject.domain.trim()) return;

    setError('');
    setIsCreatingProject(true);
    try {
      await api.createProject({
        name: newProject.client_name.trim(),
        domain: newProject.domain.trim().replace(/^https?:\/\//, '').replace(/\/$/, ''),
        ga4_property_id: newProject.ga4_property_id.trim() || null
      });
      setShowAddModal(false);
      setNewProject({ client_name: '', domain: '', ga4_property_id: '' });
      await loadProjects();
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
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete project');
    }
  };

  const handleCrawl = async (projectId: string) => {
    setError('');
    setStartingCrawlProjectId(projectId);
    try {
      const crawl = await api.startCrawl(projectId, {
        max_pages: 500,
        delay: 1,
        max_depth: 8,
        seed_urls: WEBSITE_CONTEXT_SEED_URLS
      });
      navigate(`/crawl/${crawl.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start crawl');
      setStartingCrawlProjectId('');
    }
  };

  const handleRecrawl = async (projectId: string) => {
    setError('');
    setStartingCrawlProjectId(projectId);
    try {
      const crawl = await api.recrawlProject(projectId, {
        max_pages: 500,
        delay: 1,
        max_depth: 8,
        seed_urls: WEBSITE_CONTEXT_SEED_URLS
      });
      navigate(`/crawl/${crawl.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restart crawl');
      setStartingCrawlProjectId('');
    }
  };

  const handleReaudit = async (projectId: string) => {
    setError('');
    setStartingAuditProjectId(projectId);
    try {
      const audit = await api.reauditProject(projectId);
      navigate(`/audit/${audit.audit_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rerun audit');
      setStartingAuditProjectId('');
    }
  };

  const handlePreflight = async (projectId: string) => {
    setError('');
    setRunningPreflightProjectId(projectId);
    try {
      const report = await api.runProjectPreflight(projectId);
      setPreflightReports((current) => ({ ...current, [projectId]: report }));
      setExpandedPreflightProjectId(projectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run preflight scan');
    } finally {
      setRunningPreflightProjectId('');
    }
  };

  const formatConfidence = (report?: PreflightReport) => {
    if (!report || report.status === 'not_run' || report.confidence == null) return '-';
    return `${Math.round(report.confidence * 100)}%`;
  };

  const renderStatusBadge = (status?: string) => {
    if (!status || status === 'never_crawled') {
      return <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600">Never Crawled</span>;
    }
    if (status === 'completed') {
      return <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-700">Audit Ready</span>;
    }
    if (status === 'running' || status === 'pending') {
      return <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-700">Crawl Running</span>;
    }
    return <span className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-700">Crawl Failed</span>;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Client Folders</h1>
          <p className="text-gray-500 mt-1">Create folders by client name and manage crawls</p>
        </div>
        <button onClick={() => setShowAddModal(true)} className="btn-primary flex items-center gap-2">
          <FolderPlus className="w-5 h-5" />
          Create New Folder
        </button>
      </div>

      {error && <div className="card text-red-600">{error}</div>}

      {(hasActiveCrawl || startingCrawlProjectId || startingAuditProjectId) && (
        <div className="card border-blue-200 bg-blue-50">
          <div className="flex items-center justify-between gap-4 mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center">
                <Activity className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <h2 className="font-bold text-gray-900">
                  {startingAuditProjectId ? 'Audit starting' : startingCrawlProjectId ? 'Crawl starting' : 'Crawl running'}
                </h2>
                <p className="text-sm text-gray-600">Active work refreshes automatically from the local backend.</p>
              </div>
            </div>
            <span className="px-3 py-1 rounded-full bg-blue-100 text-blue-700 text-sm font-semibold">Working</span>
          </div>
          <div className="h-3 bg-white rounded-full overflow-hidden border border-blue-100">
            <div className="h-full w-2/3 bg-blue-600 progress-slide" />
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="card text-gray-500">Loading projects...</div>
      ) : projects.length === 0 ? (
        <div className="card text-gray-500">No projects have been created yet.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => {
            const isProjectCrawlActive = ACTIVE_CRAWL_STATUSES.has(project.latest_crawl_status || '');
            const isStartingCrawl = startingCrawlProjectId === project.id;
            const isStartingAudit = startingAuditProjectId === project.id;
            const isRunningPreflight = runningPreflightProjectId === project.id;
            const preflight = preflightReports[project.id];
            const preflightHasReport = !!preflight && preflight.status !== 'not_run' && preflight.pages_scanned != null;
            const detected = preflight?.detected || {};
            return (
            <div key={project.id} className="card hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-brand-orange/10 rounded-xl flex items-center justify-center">
                    <Globe className="w-6 h-6 text-brand-orange" />
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-900">{project.name}</h3>
                    <p className="text-sm text-gray-500">{project.domain}</p>
                    <div className="mt-1">{renderStatusBadge(project.latest_crawl_status)}</div>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(project.id)}
                  className="p-2 hover:bg-red-50 rounded-lg text-gray-400 hover:text-red-600 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              <div className="mb-4 rounded-lg border border-cyan-100 bg-cyan-50 px-3 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-brand-accent" />
                    <div>
                      <p className="text-sm font-semibold text-gray-900">Preflight</p>
                      <p className="text-xs text-gray-600">
                        {preflightHasReport
                          ? `${preflight.pages_scanned} pages scanned · ${formatConfidence(preflight)} confidence`
                          : 'Not run yet'}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handlePreflight(project.id)}
                    disabled={isRunningPreflight}
                    className="px-3 py-1.5 rounded-lg bg-white text-brand-accent text-xs font-semibold hover:bg-cyan-100 transition-colors disabled:opacity-50 flex items-center gap-1"
                  >
                    {isRunningPreflight && <Activity className="w-3 h-3 animate-pulse" />}
                    {isRunningPreflight ? 'Running' : preflightHasReport ? 'Re-run' : 'Run'}
                  </button>
                </div>
                {preflightHasReport && (
                  <>
                    <div className="grid grid-cols-3 gap-2 mt-3 text-center">
                      <div className="rounded bg-white px-2 py-2">
                        <p className="text-sm font-bold text-gray-900">{detected.sitemap_xml ? 'Yes' : 'No'}</p>
                        <p className="text-[11px] text-gray-500">Sitemap</p>
                      </div>
                      <div className="rounded bg-white px-2 py-2">
                        <p className="text-sm font-bold text-gray-900">{detected.has_auth_pages ? 'Yes' : 'No'}</p>
                        <p className="text-[11px] text-gray-500">Auth</p>
                      </div>
                      <div className="rounded bg-white px-2 py-2">
                        <p className="text-sm font-bold text-gray-900">{detected.has_products ? 'Yes' : 'No'}</p>
                        <p className="text-[11px] text-gray-500">Products</p>
                      </div>
                    </div>
                    <button
                      onClick={() => setExpandedPreflightProjectId(expandedPreflightProjectId === project.id ? '' : project.id)}
                      className="mt-3 text-xs font-semibold text-brand-accent hover:text-brand-dark"
                    >
                      {expandedPreflightProjectId === project.id ? 'Hide details' : 'View details'}
                    </button>
                    {expandedPreflightProjectId === project.id && (
                      <div className="mt-3 rounded bg-white px-3 py-3 text-xs text-gray-700 space-y-2">
                        <div className="flex justify-between gap-3">
                          <span>Install mode</span>
                          <span className="font-semibold text-right">{preflight.recommended_install_mode || '-'}</span>
                        </div>
                        <div className="flex justify-between gap-3">
                          <span>Robots</span>
                          <span className="font-semibold">{detected.robots_txt ? 'Present' : 'Missing'}</span>
                        </div>
                        <div className="flex justify-between gap-3">
                          <span>Blog</span>
                          <span className="font-semibold">{detected.has_blog ? 'Detected' : 'No'}</span>
                        </div>
                        <div className="flex justify-between gap-3">
                          <span>Warnings</span>
                          <span className="font-semibold">{preflight.warnings?.length || 0}</span>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>

              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <p className={`text-2xl font-bold ${project.latest_audit_score == null ? 'text-gray-400' : 'text-gray-900'}`}>
                    {project.latest_audit_score == null ? '-' : Math.round(project.latest_audit_score)}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Score</p>
                </div>
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <p className={`text-2xl font-bold ${project.latest_pages_crawled == null ? 'text-gray-400' : 'text-gray-900'}`}>
                    {project.latest_pages_crawled ?? '-'}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Pages</p>
                </div>
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm font-bold text-gray-900">
                    {project.created_at ? new Date(project.created_at).toLocaleDateString() : '-'}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Created</p>
                </div>
              </div>

              {(isProjectCrawlActive || isStartingCrawl || isStartingAudit) && (
                <div className="mb-4 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2">
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="font-medium text-blue-700">{isStartingAudit ? 'Starting audit' : isStartingCrawl ? 'Starting crawl' : 'Crawl running'}</span>
                    <Activity className="w-4 h-4 text-blue-700 animate-pulse" />
                  </div>
                  <div className="h-2 bg-white rounded-full overflow-hidden">
                    <div className="h-full w-3/4 bg-blue-600 progress-slide" />
                  </div>
                </div>
              )}

              <div className="flex gap-2">
                <button
                  onClick={() =>
                    project.latest_crawl_id ? handleRecrawl(project.id) : handleCrawl(project.id)
                  }
                  disabled={isStartingCrawl || isProjectCrawlActive}
                  className="flex-1 py-2 bg-brand-orange/10 text-brand-orange rounded-lg font-medium hover:bg-brand-orange/20 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {isStartingCrawl || isProjectCrawlActive ? <Activity className="w-4 h-4 animate-pulse" /> : project.latest_crawl_id ? <RotateCw className="w-4 h-4" /> : <ExternalLink className="w-4 h-4" />}
                  {isStartingCrawl ? 'Starting...' : isProjectCrawlActive ? 'Running' : project.latest_crawl_id ? 'Re-Crawl' : 'Crawl'}
                </button>
                {project.latest_crawl_status === 'completed' && (
                  <button
                    onClick={() => handleReaudit(project.id)}
                    disabled={isStartingAudit}
                    className="flex-1 py-2 bg-purple-50 text-purple-700 rounded-lg font-medium hover:bg-purple-100 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {isStartingAudit && <Activity className="w-4 h-4 animate-pulse" />}
                    {isStartingAudit ? 'Starting...' : 'Re-Audit'}
                  </button>
                )}
                {project.ga4_property_id && (
                  <button
                    onClick={() => navigate(`/ga4/${project.ga4_property_id}`)}
                    className="flex-1 py-2 bg-blue-50 text-blue-600 rounded-lg font-medium hover:bg-blue-100 transition-colors flex items-center justify-center gap-2"
                  >
                    <BarChart3 className="w-4 h-4" />
                    GA4
                  </button>
                )}
                <button
                  onClick={() => navigate(`/reports/${project.id}`)}
                  className="flex-1 py-2 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors flex items-center justify-center gap-2"
                >
                  <FileText className="w-4 h-4" />
                  Reports
                </button>
              </div>
            </div>
          )})}
        </div>
      )}

      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-8 w-full max-w-md">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Create New Folder</h2>
            {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Client Name</label>
                <input
                  type="text"
                  value={newProject.client_name}
                  onChange={(e) => setNewProject({ ...newProject, client_name: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-brand-orange"
                  placeholder="Client name (used as folder title)"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Domain</label>
                <input
                  type="text"
                  value={newProject.domain}
                  onChange={(e) => setNewProject({ ...newProject, domain: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-brand-orange"
                  placeholder="domain.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">GA4 Property ID</label>
                <input
                  type="text"
                  value={newProject.ga4_property_id}
                  onChange={(e) => setNewProject({ ...newProject, ga4_property_id: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-brand-orange"
                  placeholder="Optional"
                />
              </div>
            </div>

            <div className="flex gap-4 mt-8">
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setError('');
                }}
                disabled={isCreatingProject}
                className="flex-1 py-3 border border-gray-300 rounded-lg font-medium hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddProject}
                disabled={isCreatingProject || !newProject.client_name.trim() || !newProject.domain.trim()}
                className="flex-1 py-3 bg-brand-orange text-brand-dark rounded-lg font-medium hover:bg-brand-accent hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isCreatingProject ? 'Creating...' : 'Create Folder'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Projects;
