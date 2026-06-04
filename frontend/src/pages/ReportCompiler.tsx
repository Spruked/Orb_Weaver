import React, { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { FileText, Download, RefreshCw } from 'lucide-react';
import { api, ReportCompilerPayload, downloads } from '../services/api';

const ReportCompiler: React.FC = () => {
  const { projectId } = useParams();
  const [data, setData] = useState<ReportCompilerPayload | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!projectId) return;
    setIsLoading(true);
    setError('');
    try {
      const payload = await api.getReportCompiler(projectId);
      setData(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load report compiler');
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  if (isLoading) return <div className="card text-gray-500">Loading report compiler...</div>;
  if (error) return <div className="card text-red-600">{error}</div>;
  if (!data) return <div className="card text-gray-500">Report compiler not found.</div>;

  const latestAuditId = data.latest_audit?.id;
  const latestCrawlId = data.latest_crawl?.id;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Report Compiler</h1>
          <p className="text-gray-500 mt-1">{data.project.name} - {data.project.domain}</p>
        </div>
        <button onClick={load} className="btn-secondary flex items-center gap-2">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
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
              <li key={file} className="text-sm text-gray-700 bg-gray-50 rounded-lg px-3 py-2">
                {file}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default ReportCompiler;
