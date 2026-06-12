import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Globe,
  Search,
  BarChart3,
  ArrowRight,
  AlertTriangle,
  CheckCircle,
  Zap,
  Clock,
  ChevronRight,
  Activity,
  ShieldCheck
} from 'lucide-react';
import ScoreCircle from '../components/ScoreCircle';
import IssueCard from '../components/IssueCard';
import { api, Customer, PreflightReport, Project, SEOIssue } from '../services/api';

const ACTIVE_CRAWL_STATUSES = new Set(['pending', 'running']);

const ProcessActivityPanel: React.FC<{
  title: string;
  business?: string;
  domain?: string;
  status?: string;
  detail: string;
  progress: number;
}> = ({ title, business, domain, status, detail, progress }) => (
  <div className="card border-blue-200 bg-blue-50">
    <div className="flex items-start justify-between gap-4 mb-4">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center">
          <Activity className="w-5 h-5 animate-pulse" />
        </div>
        <div>
          <h2 className="font-bold text-gray-900">{title}</h2>
          <p className="text-lg font-bold text-gray-900 mt-1">{business || 'Pending website'}</p>
          <p className="text-sm text-gray-700">{domain || detail}</p>
          {status && <p className="text-xs text-blue-700 font-semibold mt-1">Status: {status}</p>}
          <p className="text-xs text-gray-600 mt-1">{detail}</p>
        </div>
      </div>
      <span className="text-2xl font-bold text-blue-700">{progress}%</span>
    </div>
    <div className="h-3 bg-white rounded-full overflow-hidden border border-blue-100">
      <div className="h-full bg-blue-600 progress-slide transition-all duration-700" style={{ width: `${progress}%` }} />
    </div>
  </div>
);

const statusBadgeClass = (status?: string) => {
  if (!status || status === 'never_crawled') return 'bg-gray-100 text-gray-700';
  if (status === 'completed') return 'bg-green-100 text-green-700';
  if (status === 'running' || status === 'pending') return 'bg-blue-100 text-blue-700';
  return 'bg-red-100 text-red-700';
};

interface DashboardProps {
  customer: Customer;
}

const Dashboard: React.FC<DashboardProps> = ({ customer }) => {
  const navigate = useNavigate();
  const [domain, setDomain] = useState('');
  const [competitorDomains, setCompetitorDomains] = useState('');
  const [projects, setProjects] = useState<Project[]>([]);
  const [dashboardData, setDashboardData] = useState<{
    crawl_summary?: Record<string, number | boolean> | null;
    audit_scores?: Record<string, number> | null;
    audit_issues?: {
      total_issues: number;
      critical_count: number;
      warning_count: number;
      opportunity_count: number;
      total_pages: number;
      avg_load_time: number;
    } | null;
    ga4_data?: {
      traffic_overview?: { totals?: Record<string, number> };
      device_breakdown?: Array<Record<string, string | number>>;
    } | null;
    top_issues?: SEOIssue[] | null;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCrawling, setIsCrawling] = useState(false);
  const [isRunningPreflight, setIsRunningPreflight] = useState(false);
  const [preflightReport, setPreflightReport] = useState<PreflightReport | null>(null);
  const [error, setError] = useState('');
  const [processProgress, setProcessProgress] = useState(8);

  const latestProject = useMemo(() => projects[projects.length - 1], [projects]);
  const scores = dashboardData?.audit_scores;
  const summary = dashboardData?.audit_issues;
  const topIssues = dashboardData?.top_issues || [];
  const sessions = dashboardData?.ga4_data?.traffic_overview?.totals?.sessions || 0;
  const devices = dashboardData?.ga4_data?.device_breakdown || [];
  const enteredDomain = domain.trim().replace(/^https?:\/\//, '').replace(/\/$/, '');
  const activeBusiness = latestProject?.name || (enteredDomain ? 'New website scan' : 'No active website selected');
  const activeDomain = latestProject?.domain || enteredDomain || 'Enter a website URL to start a scan';
  const activeCrawlStatus = isCrawling ? 'queueing' : latestProject?.latest_crawl_status || 'not started';
  const activeAuditStatus = latestProject?.latest_audit_id
    ? `audit #${latestProject.latest_audit_id}${latestProject.latest_audit_score == null ? ' compiling' : ` score ${Math.round(latestProject.latest_audit_score)}`}`
    : 'no audit report yet';

  const loadDashboard = useCallback(async (showLoading = true) => {
    if (showLoading) {
      setIsLoading(true);
    }
      setError('');
      try {
        const projectList = await api.listProjects();
        setProjects(projectList);

        const latest = projectList[projectList.length - 1];
        if (latest) {
          const [combined, preflight] = await Promise.all([
            api.getCombinedDashboard(latest.id),
            api.getProjectPreflight(latest.id).catch(() => null)
          ]);
          setDashboardData(combined);
          setPreflightReport(preflight);
        } else {
          setDashboardData(null);
          setPreflightReport(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      } finally {
        if (showLoading) {
          setIsLoading(false);
        }
      }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const hasActiveCrawl = !!latestProject?.latest_crawl_status && ACTIVE_CRAWL_STATUSES.has(latestProject.latest_crawl_status);
  const hasActiveAudit = !!latestProject?.latest_audit_id && latestProject.latest_audit_score == null && latestProject.latest_crawl_status === 'completed';
  const hasActiveProcess = isCrawling || hasActiveCrawl || hasActiveAudit;

  useEffect(() => {
    if (!hasActiveProcess) {
      setProcessProgress(100);
      return;
    }

    setProcessProgress((current) => (current >= 95 ? 8 : Math.max(current, 8)));
    const progressTimer = window.setInterval(() => {
      setProcessProgress((current) => Math.min(95, current + 1));
    }, 1000);
    const pollTimer = window.setInterval(() => {
      loadDashboard(false);
    }, 4000);

    return () => {
      window.clearInterval(progressTimer);
      window.clearInterval(pollTimer);
    };
  }, [hasActiveProcess, loadDashboard]);

  const handleStartCrawl = async () => {
    if (!domain.trim()) return;

    setIsCrawling(true);
    setError('');
    try {
      const normalizedDomain = domain.trim().replace(/^https?:\/\//, '').replace(/\/$/, '');
      const project = await api.createProject({
        domain: normalizedDomain,
        ga4_property_id: null
      });
      const crawl = await api.startCrawl(project.id, {
        max_pages: 150,
        delay: 1,
        max_depth: 5,
        competitor_domains: competitorDomains
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean)
      });
      navigate(`/crawl/${crawl.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start crawl');
    } finally {
      setIsCrawling(false);
    }
  };

  const handleRunPreflight = async () => {
    if (!latestProject) return;

    setIsRunningPreflight(true);
    setError('');
    try {
      setPreflightReport(await api.runProjectPreflight(latestProject.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run preflight scan');
    } finally {
      setIsRunningPreflight(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-blue-600';
    if (score >= 40) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="space-y-8">
      <div className="bg-gradient-to-r from-brand-dark to-brand-blue rounded-2xl p-8 text-white">
        <div className="grid grid-cols-1 xl:grid-cols-[1.1fr_0.9fr] gap-8">
          <div>
            <p className="text-sm text-gray-300 mb-2">Dashboard for</p>
            <h1 className="text-4xl font-bold mb-2">{customer.business_name}</h1>
            <p className="text-gray-300 text-sm mb-6">
              {customer.contact_name || 'Account owner'} · {customer.email}
            </p>

            <div className="rounded-xl border border-white/15 bg-white/10 p-5 mb-8">
              <p className="text-sm text-gray-300">Current website</p>
              <div className="flex flex-wrap items-center gap-3 mt-2">
                <h2 className="text-2xl font-bold">{activeBusiness}</h2>
                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${statusBadgeClass(activeCrawlStatus)}`}>
                  Crawl: {activeCrawlStatus}
                </span>
              </div>
              <p className="text-lg text-white mt-1">{activeDomain}</p>
              <p className="text-sm text-gray-300 mt-2">Audit: {activeAuditStatus}</p>
            </div>

          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Enter your website URL"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                className="w-full pl-12 pr-4 py-4 rounded-xl bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:border-brand-orange"
              />
            </div>
            <button
              onClick={handleStartCrawl}
              disabled={isCrawling || !domain.trim()}
              className="bg-brand-orange hover:bg-brand-accent text-brand-dark hover:text-white px-8 py-4 rounded-xl font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isCrawling ? <Clock className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
              {isCrawling ? 'Starting...' : 'Start Audit'}
            </button>
          </div>

          <div className="mt-4 relative">
            <input
              type="text"
              placeholder="Optional competitors, comma-separated"
              value={competitorDomains}
              onChange={(e) => setCompetitorDomains(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:border-brand-orange"
            />
          </div>

          {error && <p className="mt-4 text-sm text-red-200">{error}</p>}
          </div>

          <div className="rounded-xl border border-white/15 bg-white/10 p-5 self-start">
            <h2 className="text-lg font-bold mb-4">Displayed Data</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between gap-4">
                <span className="text-gray-300">Business</span>
                <span className="font-semibold text-right">{customer.business_name}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-gray-300">Website</span>
                <span className="font-semibold text-right">{activeDomain}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-gray-300">Crawl Job</span>
                <span className="font-semibold text-right">{latestProject?.latest_crawl_id ? `#${latestProject.latest_crawl_id}` : 'none'}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-gray-300">Audit Report</span>
                <span className="font-semibold text-right">{latestProject?.latest_audit_id ? `#${latestProject.latest_audit_id}` : 'none'}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-gray-300">Pages Crawled</span>
                <span className="font-semibold text-right">{latestProject?.latest_pages_crawled ?? 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {hasActiveProcess && (
        <ProcessActivityPanel
          title={isCrawling ? 'Starting scan' : hasActiveAudit ? 'Audit report compiling' : 'Site scan running'}
          business={isCrawling ? enteredDomain : latestProject?.name}
          domain={isCrawling ? enteredDomain : latestProject?.domain}
          status={isCrawling ? 'queueing' : hasActiveAudit ? 'audit compiling' : latestProject?.latest_crawl_status}
          detail={isCrawling ? 'Creating project and queueing crawl job' : hasActiveAudit ? 'Scoring crawl data and writing report files' : 'Live crawl job is active for this website'}
          progress={processProgress}
        />
      )}

      {isLoading ? (
        <div className="card text-gray-500">Loading live dashboard data...</div>
      ) : !latestProject ? (
        <div className="card text-gray-500">No live project data yet. Start an audit to populate this dashboard.</div>
      ) : (
        <>
          <div className="card border-cyan-100 bg-cyan-50">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex items-start gap-3">
                <div className="w-11 h-11 rounded-lg bg-white text-brand-accent flex items-center justify-center">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-gray-900">Preflight Readiness</h2>
                  <p className="text-sm text-gray-600">
                    {preflightReport && preflightReport.status !== 'not_run'
                      ? `${preflightReport.pages_scanned || 0} pages scanned for ${latestProject.domain}`
                      : `No preflight report has been run for ${latestProject.domain}`}
                  </p>
                </div>
              </div>
              <button
                onClick={handleRunPreflight}
                disabled={isRunningPreflight}
                className="px-4 py-2 rounded-lg bg-brand-orange text-brand-dark font-semibold hover:bg-brand-accent hover:text-white transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isRunningPreflight && <Activity className="w-4 h-4 animate-pulse" />}
                {isRunningPreflight ? 'Running Preflight' : preflightReport?.status !== 'not_run' ? 'Re-run Preflight' : 'Run Preflight'}
              </button>
            </div>

            {preflightReport && preflightReport.status !== 'not_run' ? (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-5">
                <div className="rounded-lg bg-white px-3 py-3">
                  <p className="text-xl font-bold text-gray-900">{preflightReport.pages_scanned || 0}</p>
                  <p className="text-xs text-gray-500">Pages</p>
                </div>
                <div className="rounded-lg bg-white px-3 py-3">
                  <p className="text-xl font-bold text-gray-900">
                    {preflightReport.confidence == null ? '-' : `${Math.round(preflightReport.confidence * 100)}%`}
                  </p>
                  <p className="text-xs text-gray-500">Confidence</p>
                </div>
                <div className="rounded-lg bg-white px-3 py-3">
                  <p className="text-xl font-bold text-gray-900">{preflightReport.detected?.sitemap_xml ? 'Yes' : 'No'}</p>
                  <p className="text-xs text-gray-500">Sitemap</p>
                </div>
                <div className="rounded-lg bg-white px-3 py-3">
                  <p className="text-xl font-bold text-gray-900">{preflightReport.detected?.has_auth_pages ? 'Yes' : 'No'}</p>
                  <p className="text-xs text-gray-500">Auth Pages</p>
                </div>
                <div className="rounded-lg bg-white px-3 py-3">
                  <p className="text-xl font-bold text-gray-900">{preflightReport.warnings?.length || 0}</p>
                  <p className="text-xs text-gray-500">Warnings</p>
                </div>
              </div>
            ) : null}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-700">Overall Score</h3>
                <Zap className="w-5 h-5 text-brand-orange" />
              </div>
              {scores?.overall !== undefined ? (
                <div className="flex items-center gap-4">
                  <ScoreCircle score={Math.round(scores.overall)} size="sm" />
                  <p className={`text-2xl font-bold ${getScoreColor(scores.overall)}`}>
                    {Math.round(scores.overall)}/100
                  </p>
                </div>
              ) : (
                <p className="text-gray-500">No audit report yet</p>
              )}
            </div>

            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-700">GA4 Sessions</h3>
                <BarChart3 className="w-5 h-5 text-green-500" />
              </div>
              <p className="text-3xl font-bold text-gray-900">{sessions.toLocaleString()}</p>
              <p className="text-sm text-gray-500 mt-1">Live GA4 total when connected</p>
            </div>

            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-700">Pages Crawled</h3>
                <Globe className="w-5 h-5 text-blue-500" />
              </div>
              <p className="text-3xl font-bold text-gray-900">
                {Number(dashboardData?.crawl_summary?.total_pages || summary?.total_pages || 0)}
              </p>
              <p className="text-sm text-gray-500 mt-1">{summary?.critical_count || 0} critical issues found</p>
            </div>

            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-700">Avg Load Time</h3>
                <Clock className="w-5 h-5 text-yellow-500" />
              </div>
              <p className="text-3xl font-bold text-gray-900">
                {summary?.avg_load_time ? `${(summary.avg_load_time / 1000).toFixed(2)}s` : '-'}
              </p>
              <p className="text-sm text-gray-500 mt-1">From the latest completed crawl</p>
            </div>
          </div>

          {scores && (
            <div className="card">
              <h2 className="text-xl font-bold text-gray-900 mb-6">SEO Score Breakdown</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-6">
                {Object.entries(scores).map(([key, score]) => (
                  <div key={key} className="text-center">
                    <ScoreCircle score={Math.round(score)} size="sm" />
                    <p className="mt-2 text-sm font-medium text-gray-600 capitalize">{key}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-gray-900">Top Issues</h2>
                <button
                  onClick={() => navigate('/projects')}
                  className="text-brand-accent hover:text-brand-blue font-medium flex items-center gap-1"
                >
                  View Projects <ChevronRight className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-4">
                {topIssues.length > 0 ? (
                  topIssues.map((issue, idx) => <IssueCard key={idx} issue={issue} />)
                ) : (
                  <div className="card text-gray-500">No audit issues available yet.</div>
                )}
              </div>
            </div>

            <div className="space-y-6">
              <div className="card">
                <h3 className="font-bold text-gray-900 mb-4">Issues Breakdown</h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <AlertTriangle className="w-5 h-5 text-red-600" />
                      <span className="font-medium text-red-700">Critical</span>
                    </div>
                    <span className="text-xl font-bold text-red-700">{summary?.critical_count || 0}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <AlertTriangle className="w-5 h-5 text-yellow-600" />
                      <span className="font-medium text-yellow-700">Warnings</span>
                    </div>
                    <span className="text-xl font-bold text-yellow-700">{summary?.warning_count || 0}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <CheckCircle className="w-5 h-5 text-blue-600" />
                      <span className="font-medium text-blue-700">Opportunities</span>
                    </div>
                    <span className="text-xl font-bold text-blue-700">{summary?.opportunity_count || 0}</span>
                  </div>
                </div>
              </div>

              <div className="card">
                <h3 className="font-bold text-gray-900 mb-4">Device Breakdown</h3>
                <div className="space-y-3">
                  {devices.length > 0 ? (
                    devices.map((device) => {
                      const deviceSessions = Number(device.sessions || 0);
                      const percent = sessions > 0 ? (deviceSessions / sessions) * 100 : 0;
                      return (
                        <div key={String(device.device || device.name)}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium capitalize text-gray-700">
                              {String(device.device || device.name)}
                            </span>
                            <span className="text-sm text-gray-500">{percent.toFixed(1)}%</span>
                          </div>
                          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div className="h-full bg-brand-orange rounded-full" style={{ width: `${percent}%` }} />
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <p className="text-gray-500">No GA4 device data available.</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div onClick={() => navigate('/projects')} className="card cursor-pointer hover:shadow-md transition-shadow group">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center group-hover:bg-blue-200 transition-colors">
                  <Globe className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-900">Manage Projects</h3>
                  <p className="text-sm text-gray-500">Add and configure websites</p>
                </div>
                <ArrowRight className="w-5 h-5 text-gray-400 ml-auto group-hover:text-brand-orange transition-colors" />
              </div>
            </div>

            {latestProject.ga4_property_id && (
              <div
                onClick={() => navigate(`/ga4/${latestProject.ga4_property_id}`)}
                className="card cursor-pointer hover:shadow-md transition-shadow group"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center group-hover:bg-green-200 transition-colors">
                    <BarChart3 className="w-6 h-6 text-green-600" />
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-900">GA4 Analytics</h3>
                    <p className="text-sm text-gray-500">View connected property data</p>
                  </div>
                  <ArrowRight className="w-5 h-5 text-gray-400 ml-auto group-hover:text-brand-orange transition-colors" />
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default Dashboard;
