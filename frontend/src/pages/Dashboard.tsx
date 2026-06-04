import React, { useEffect, useMemo, useState } from 'react';
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
  ChevronRight
} from 'lucide-react';
import ScoreCircle from '../components/ScoreCircle';
import IssueCard from '../components/IssueCard';
import { api, Project, SEOIssue } from '../services/api';

const Dashboard: React.FC = () => {
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
  const [error, setError] = useState('');

  const latestProject = useMemo(() => projects[projects.length - 1], [projects]);
  const scores = dashboardData?.audit_scores;
  const summary = dashboardData?.audit_issues;
  const topIssues = dashboardData?.top_issues || [];
  const sessions = dashboardData?.ga4_data?.traffic_overview?.totals?.sessions || 0;
  const devices = dashboardData?.ga4_data?.device_breakdown || [];

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      setError('');
      try {
        const projectList = await api.listProjects();
        setProjects(projectList);

        const latest = projectList[projectList.length - 1];
        if (latest) {
          setDashboardData(await api.getCombinedDashboard(latest.id));
        } else {
          setDashboardData(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      } finally {
        setIsLoading(false);
      }
    };

    load();
  }, []);

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
        max_pages: 100,
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

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-blue-600';
    if (score >= 40) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="space-y-8">
      <div className="bg-gradient-to-r from-brand-dark to-brand-blue rounded-2xl p-8 text-white">
        <div className="max-w-3xl">
          <h1 className="text-4xl font-bold mb-4">Orb Weaver</h1>
          <p className="text-gray-300 text-lg mb-8">
            Website ORB Intelligence Engine for crawl analysis, semantic scoring, authority flow, and local reporting.
          </p>

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
              className="bg-brand-orange hover:bg-orange-600 text-white px-8 py-4 rounded-xl font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
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
      </div>

      {isLoading ? (
        <div className="card text-gray-500">Loading live dashboard data...</div>
      ) : !latestProject ? (
        <div className="card text-gray-500">No live project data yet. Start an audit to populate this dashboard.</div>
      ) : (
        <>
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
                  className="text-brand-orange hover:text-orange-700 font-medium flex items-center gap-1"
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
