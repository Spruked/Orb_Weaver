import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, Download, Eye, FileText, RefreshCw, RotateCw, Search, ShieldCheck } from 'lucide-react';
import { api, CrawlJob, downloads } from '../services/api';

const ACTIVE_STATUSES = new Set(['pending', 'running']);
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

const statusClass = (status: string) => {
  if (status === 'completed') return 'bg-green-100 text-green-700';
  if (ACTIVE_STATUSES.has(status)) return 'bg-blue-100 text-blue-700';
  if (status === 'failed') return 'bg-red-100 text-red-700';
  return 'bg-gray-100 text-gray-600';
};

const formatDate = (value?: string) => {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleString();
};

const formatDuration = (job: CrawlJob) => {
  if (!job.start_time || !job.end_time) return '-';
  const ms = new Date(job.end_time).getTime() - new Date(job.start_time).getTime();
  if (Number.isNaN(ms) || ms < 0) return '-';
  const seconds = Math.round(ms / 1000);
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
};

const CrawlJobs: React.FC = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<CrawlJob[]>([]);
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [recrawlingJobId, setRecrawlingJobId] = useState('');
  const [error, setError] = useState('');

  const loadJobs = async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    setError('');
    try {
      setJobs(await api.listCrawlJobs());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load crawl jobs');
    } finally {
      if (showLoading) setIsLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const hasActiveJob = jobs.some((job) => ACTIVE_STATUSES.has(job.status));

  useEffect(() => {
    if (!hasActiveJob) return;
    const timer = window.setInterval(() => loadJobs(false), 2500);
    return () => window.clearInterval(timer);
  }, [hasActiveJob]);

  const filteredJobs = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return jobs;
    return jobs.filter((job) =>
      [job.id, job.project_name, job.project_domain, job.status]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(needle))
    );
  }, [jobs, query]);

  const runAudit = async (job: CrawlJob) => {
    setError('');
    try {
      const audit = await api.runAudit(job.id);
      navigate(`/audit/${audit.audit_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start audit');
    }
  };

  const recrawlJob = async (job: CrawlJob) => {
    setError('');
    setRecrawlingJobId(job.id);
    try {
      const crawl = await api.recrawlProject(job.project_id, {
        max_pages: Number(job.config?.max_pages || 500),
        delay: Number(job.config?.delay || 1),
        max_depth: Number(job.config?.max_depth || 8),
        competitor_domains: job.config?.competitor_domains || [],
        seed_urls: job.config?.seed_urls?.length ? job.config.seed_urls : WEBSITE_CONTEXT_SEED_URLS
      });
      navigate(`/crawl/${crawl.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restart crawl');
    } finally {
      setRecrawlingJobId('');
    }
  };

  if (isLoading) return <div className="card text-gray-500">Loading crawl jobs...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Crawl Jobs</h1>
          <p className="text-gray-500 mt-1">Account crawl history and active scan queue</p>
        </div>
        <button onClick={() => loadJobs()} className="btn-secondary flex items-center gap-2">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {error && <div className="card text-red-600">{error}</div>}

      {hasActiveJob && (
        <div className="card border-blue-200 bg-blue-50">
          <div className="flex items-center justify-between gap-4 mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center">
                <Activity className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <h2 className="font-bold text-gray-900">Active crawl running</h2>
                <p className="text-sm text-gray-600">This page refreshes active jobs automatically.</p>
              </div>
            </div>
            <span className="px-3 py-1 rounded-full bg-blue-100 text-blue-700 text-sm font-semibold">Working</span>
          </div>
          <div className="h-3 bg-white rounded-full overflow-hidden border border-blue-100">
            <div className="h-full w-2/3 bg-blue-600 progress-slide" />
          </div>
        </div>
      )}

      <div className="card">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by client, domain, status, or job id"
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-brand-orange"
          />
        </div>
      </div>

      {jobs.length === 0 ? (
        <div className="card text-gray-500">No crawl jobs have been created for this account yet.</div>
      ) : filteredJobs.length === 0 ? (
        <div className="card text-gray-500">No crawl jobs match this search.</div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Job</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Client</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Pages</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Started</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Duration</th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredJobs.map((job) => {
                const isActive = ACTIVE_STATUSES.has(job.status);
                return (
                <tr key={job.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <p className="text-sm font-bold text-gray-900">#{job.id}</p>
                    <p className="text-xs text-gray-500">Project {job.project_id}</p>
                  </td>
                  <td className="px-6 py-4">
                    <p className="text-base font-bold text-gray-900">{job.project_name || '-'}</p>
                    <p className="text-sm text-gray-700">{job.project_domain || '-'}</p>
                  </td>
                  <td className="px-6 py-4">
                    <div className="space-y-2">
                      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${statusClass(job.status)}`}>
                        {job.status}
                      </span>
                      {isActive && (
                        <div className="h-2 w-28 bg-blue-50 rounded-full overflow-hidden border border-blue-100">
                          <div className="h-full w-3/4 bg-blue-600 progress-slide" />
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">{job.pages_crawled || job.pages_found || 0}</td>
                  <td className="px-6 py-4 text-sm text-gray-700">{formatDate(job.start_time || job.created_at)}</td>
                  <td className="px-6 py-4 text-sm text-gray-700">{formatDuration(job)}</td>
                  <td className="px-6 py-4">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => navigate(`/crawl/${job.id}`)}
                        className="px-3 py-2 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 flex items-center gap-2"
                      >
                        <Eye className="w-4 h-4" />
                        View
                      </button>
                      <button
                        onClick={() => downloads.crawlCsv(job.id)}
                        disabled={job.status !== 'completed'}
                        className="px-3 py-2 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-40 flex items-center gap-2"
                      >
                        <Download className="w-4 h-4" />
                        CSV
                      </button>
                      <button
                        onClick={() => recrawlJob(job)}
                        disabled={isActive || recrawlingJobId === job.id}
                        className="px-3 py-2 rounded-lg bg-cyan-50 text-brand-accent hover:bg-cyan-100 disabled:opacity-40 flex items-center gap-2"
                      >
                        <RotateCw className={`w-4 h-4 ${recrawlingJobId === job.id ? 'animate-spin' : ''}`} />
                        {recrawlingJobId === job.id ? 'Starting' : 'Recrawl'}
                      </button>
                      <button
                        onClick={() => runAudit(job)}
                        disabled={job.status !== 'completed'}
                        className="px-3 py-2 rounded-lg bg-purple-50 text-purple-700 hover:bg-purple-100 disabled:opacity-40 flex items-center gap-2"
                      >
                        <ShieldCheck className="w-4 h-4" />
                        Audit
                      </button>
                      <button
                        onClick={() => navigate(`/reports/${job.project_id}`)}
                        className="px-3 py-2 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 flex items-center gap-2"
                      >
                        <FileText className="w-4 h-4" />
                        Reports
                      </button>
                    </div>
                  </td>
                </tr>
              )})}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default CrawlJobs;
