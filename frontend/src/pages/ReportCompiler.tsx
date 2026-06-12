import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FileText, Download, RefreshCw, Eye, FolderOpen } from 'lucide-react';
import { api, Project, ReportCompilerPayload, downloads, openFiles } from '../services/api';

const ReportCompiler: React.FC = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<ReportCompilerPayload | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setIsLoading(true);
    setError('');
    try {
      if (projectId) {
        const payload = await api.getReportCompiler(projectId);
        setData(payload);
        setProjects([]);
      } else {
        const projectList = await api.listProjects();
        setProjects(projectList);
        setData(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reports');
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  if (isLoading) return <div className="card text-gray-500">Loading report compiler...</div>;
  if (error) return <div className="card text-red-600">{error}</div>;
  if (!projectId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
            <p className="text-gray-500 mt-1">Account report library</p>
          </div>
          <button onClick={load} className="btn-secondary flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>

        {projects.length === 0 ? (
          <div className="card text-gray-500">No project reports available yet.</div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {projects.map((project) => (
              <div key={project.id} className="card">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="font-bold text-gray-900">{project.name}</h2>
                    <p className="text-sm text-gray-500">{project.domain}</p>
                    <p className="text-xs text-gray-500 mt-2">
                      Crawl: {project.latest_crawl_status || 'none'} - Audit: {project.latest_audit_id ? `#${project.latest_audit_id}` : 'none'}
                    </p>
                  </div>
                  <button onClick={() => navigate(`/reports/${project.id}`)} className="btn-secondary flex items-center gap-2">
                    <FolderOpen className="w-4 h-4" />
                    Open
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (!data) return <div className="card text-gray-500">Report compiler not found.</div>;

  const latestAuditId = data.latest_audit?.id;
  const latestCrawlId = data.latest_crawl?.id;

  return (
    <div className="space-y-6">
      <div className="card border-blue-100 bg-blue-50">
        <div className="flex items-start justify-between gap-4">
        <div>
            <h1 className="text-2xl font-bold text-gray-900">{data.project.name}</h1>
            <p className="text-gray-900 font-semibold mt-1">{data.project.domain}</p>
            <p className="text-sm text-gray-600 mt-1">
              Crawl: {data.latest_crawl?.status || 'none'} · Audit: {latestAuditId ? `#${latestAuditId}` : 'none'}
            </p>
        </div>
        <button onClick={load} className="btn-secondary flex items-center gap-2">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <p className="text-sm text-gray-500">Latest Crawl</p>
          <p className="text-lg font-bold text-gray-900 mt-1">{data.latest_crawl?.status || 'None'}</p>
          <p className="text-xs text-gray-500 mt-1">Job ID: {latestCrawlId || '-'}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">Latest Audit</p>
          <p className="text-lg font-bold text-gray-900 mt-1">{latestAuditId ? `Audit #${latestAuditId}` : 'None'}</p>
          <p className="text-xs text-gray-500 mt-1">{data.latest_audit?.created_at || '-'}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">Compiled Files</p>
          <p className="text-lg font-bold text-gray-900 mt-1">{data.files.length}</p>
        </div>
      </div>

      <div className="card">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Exports</h2>
        <div className="flex flex-wrap gap-3">
          {latestCrawlId && (
            <button
              onClick={() => downloads.crawlCsv(latestCrawlId)}
              className="btn-secondary flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Crawl CSV
            </button>
          )}
          {latestAuditId && (
            <>
              <button
                onClick={() => downloads.auditCsv(latestAuditId)}
                className="btn-secondary flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Audit CSV
              </button>
              <button
                onClick={() => downloads.auditPdf(latestAuditId)}
                className="btn-secondary flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Audit PDF
              </button>
              <button
                onClick={() => openFiles.auditPdf(latestAuditId)}
                className="btn-secondary flex items-center gap-2"
              >
                <Eye className="w-4 h-4" />
                Open PDF
              </button>
            </>
          )}
        </div>
      </div>

      <div className="card">
        <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5" />
          Snapshot Files
        </h2>
        {data.files.length === 0 ? (
          <p className="text-gray-500">No compiled report files yet.</p>
        ) : (
          <ul className="space-y-2">
            {data.files.map((file) => (
              <li key={file} className="text-sm text-gray-700 bg-gray-50 rounded-lg px-3 py-2 flex items-center justify-between gap-3">
                <span className="truncate">{file}</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => openFiles.reportFile(data.project.id, file)}
                    className="px-3 py-2 rounded-lg bg-white border border-gray-200 hover:bg-gray-100 flex items-center gap-2"
                  >
                    <Eye className="w-4 h-4" />
                    Open
                  </button>
                  <button
                    onClick={() => downloads.reportFile(data.project.id, file)}
                    className="px-3 py-2 rounded-lg bg-white border border-gray-200 hover:bg-gray-100 flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    Download
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default ReportCompiler;
