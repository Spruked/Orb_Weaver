import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FileText, Download, RefreshCw, Eye, FolderOpen, Database } from 'lucide-react';
import { api, Project, ReportCompilerPayload, downloads, openFiles } from '../services/api';

const ReportCompiler: React.FC = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<ReportCompilerPayload | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'overview' | 'data'>('overview');

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
  const latestPreflight = data.latest_preflight;
  const preflightPagesScanned = latestPreflight?.pages_scanned ?? 0;
  const preflightWarnings = latestPreflight?.warnings?.length ?? 0;
  const pointerSummary = data.latest_audit?.report.pointer_summary || data.latest_crawl?.pointer_summary;
  const plannedToolCalls = data.latest_audit?.report.planned_tool_calls || data.latest_crawl?.planned_tool_calls || [];
  const inventory = data.data_inventory || [];
  const capabilityCoverage = data.capability_coverage;
  const completionContract = data.completion_contract;

  return (
    <div className="space-y-6">
      <div className="card border-blue-100 bg-blue-50">
        <div className="flex items-start justify-between gap-4">
        <div>
            <h1 className="text-2xl font-bold text-gray-900">{data.project.name}</h1>
            <p className="text-gray-900 font-semibold mt-1">{data.project.domain}</p>
            <p className="text-sm text-gray-600 mt-1">
              Preflight: {data.evidence_status?.preflight || 'not_run'} · Crawl: {data.latest_crawl?.status || 'none'} · Audit: {latestAuditId ? `#${latestAuditId}` : 'none'}
            </p>
        </div>
        <button onClick={load} className="btn-secondary flex items-center gap-2">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
        </div>
      </div>

      <div className="flex gap-2 border-b border-gray-200">
        <button
          type="button"
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-3 text-sm font-bold ${activeTab === 'overview' ? 'border-b-2 border-blue-600 text-blue-700' : 'text-gray-500'}`}
        >
          Report overview
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('data')}
          className={`inline-flex items-center gap-2 px-4 py-3 text-sm font-bold ${activeTab === 'data' ? 'border-b-2 border-blue-600 text-blue-700' : 'text-gray-500'}`}
        >
          <Database className="h-4 w-4" />
          Complete data inventory
        </button>
      </div>

      {activeTab === 'data' && (
        <div className="space-y-4">
          <div className="card border-emerald-100 bg-emerald-50">
            <p className="text-sm font-bold text-emerald-900">{data.report_access?.message || 'Report access is project-bound.'}</p>
            <p className="mt-1 text-xs text-emerald-800">The inventory lists every manufactured intelligence system. LiDAR and pointer status require live DOM verification.</p>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            {inventory.map((item) => {
              const ready = item.status === 'available';
              return (
                <article key={item.id} className="card border-gray-200">
                  <div className="flex items-start justify-between gap-4">
                    <h2 className="font-bold text-gray-900">{item.label}</h2>
                    <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${ready ? 'bg-emerald-100 text-emerald-700' : item.status.includes('blocked') ? 'bg-amber-100 text-amber-800' : 'bg-gray-100 text-gray-600'}`}>
                      {ready ? 'Available' : item.status.replaceAll('_', ' ')}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-gray-600">{item.description}</p>
                  {item.runtime_geometry_policy && <p className="mt-3 text-xs font-semibold text-amber-700">Runtime rule: live DOM geometry only.</p>}
                </article>
              );
            })}
          </div>
          {capabilityCoverage && (
            <div className="card border-indigo-100 bg-indigo-50">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">Master Capability List coverage</h2>
                  <p className="mt-1 text-sm text-gray-600">
                    {capabilityCoverage.item_count} atomic capabilities across {capabilityCoverage.category_count} systems are tracked from the persisted scan evidence.
                  </p>
                </div>
                <span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-indigo-700">{capabilityCoverage.status}</span>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-gray-700 md:grid-cols-4">
                {Object.entries(capabilityCoverage.status_counts).map(([status, count]) => (
                  <div key={status} className="rounded border border-indigo-100 bg-white px-3 py-2">
                    <span className="font-bold">{count}</span> {status.replaceAll('_', ' ')}
                  </div>
                ))}
              </div>
              <details className="mt-4 rounded border border-indigo-100 bg-white p-3">
                <summary className="cursor-pointer text-sm font-bold text-gray-900">Review all capability categories and atomic items</summary>
                <div className="mt-3 space-y-3">
                  {capabilityCoverage.categories.map((category) => (
                    <div key={category.id} className="border-b border-gray-100 pb-3 last:border-b-0">
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-semibold text-gray-900">{category.title}</p>
                        <span className="text-xs font-bold text-gray-500">{category.status.replaceAll('_', ' ')}</span>
                      </div>
                      <p className="mt-1 text-xs leading-5 text-gray-600">
                        {(category.item_evidence || category.items.map((label) => ({ label, status: category.status }))).map((item) => `${item.label} [${item.status.replaceAll('_', ' ')}]`).join(' · ')}
                      </p>
                    </div>
                  ))}
                </div>
              </details>
            </div>
          )}
          {completionContract && (
            <div className="card border-amber-100 bg-amber-50">
              <h2 className="text-lg font-bold text-gray-900">Evidence completion contract</h2>
              <p className="mt-1 text-sm text-gray-700">
                State: <span className="font-bold">{completionContract.state}</span> · {completionContract.complete_stage_count}/{completionContract.required_stage_count} required stages complete · {completionContract.authentication_wall_pages} authentication walls detected.
              </p>
              <p className="mt-2 text-xs text-amber-900">{completionContract.note}</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'overview' && <>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <p className="text-sm text-gray-500">Latest Preflight</p>
          <p className="text-lg font-bold text-gray-900 mt-1">{preflightPagesScanned ? `${preflightPagesScanned} pages` : 'None'}</p>
          <p className="text-xs text-gray-500 mt-1">{preflightWarnings} warnings · {latestPreflight?.scan_timestamp || latestPreflight?.artifact_path || '-'}</p>
        </div>
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className={`card ${pointerSummary?.status === 'passed' ? 'border-green-200 bg-green-50' : 'border-yellow-200 bg-yellow-50'}`}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm text-gray-500">ORB Pointer Guidance</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{pointerSummary?.record_count ?? 0}</p>
              <p className="text-sm text-gray-600 mt-1">
                {pointerSummary?.routes_with_pointers ?? 0} routes · {pointerSummary?.duplicate_target_ids ?? 0} duplicate IDs
              </p>
            </div>
            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${pointerSummary?.status === 'passed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
              {pointerSummary?.status || 'needs_review'}
            </span>
          </div>
        </div>

        <div className="card">
          <p className="text-sm text-gray-500 mb-3">Planned Site/Section Tool Calls</p>
          {plannedToolCalls.length > 0 ? (
            <div className="space-y-2">
              {plannedToolCalls.slice(0, 5).map((tool) => (
                <div key={tool.id} className="flex items-start justify-between gap-3 border-b border-gray-100 pb-2 last:border-b-0 last:pb-0">
                  <div>
                    <p className="font-semibold text-gray-900">{tool.tool}</p>
                    <p className="text-xs text-gray-500">{tool.section || tool.trigger}</p>
                    {tool.route && <p className="text-xs text-gray-400 truncate max-w-sm">{tool.route}</p>}
                  </div>
                  <span className={`text-xs font-semibold ${tool.requires_mcp ? 'text-purple-700' : 'text-green-700'}`}>
                    {tool.requires_mcp ? 'MCP gated' : tool.status}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No planned tool calls generated yet.</p>
          )}
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
      </>}
    </div>
  );
};

export default ReportCompiler;
