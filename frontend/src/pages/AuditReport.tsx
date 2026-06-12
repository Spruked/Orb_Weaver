import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { AlertTriangle, AlertCircle, Lightbulb, ChevronDown, ChevronUp, Download, Share2, Activity, Eye } from 'lucide-react';
import ScoreCircle from '../components/ScoreCircle';
import IssueCard from '../components/IssueCard';
import { api, AuditReportResponse, downloads, openFiles } from '../services/api';

const AuditProgressPanel: React.FC<{ progress: number }> = ({ progress }) => (
  <div className="card border-blue-200 bg-blue-50">
    <div className="flex items-start justify-between gap-4 mb-4">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center">
          <Activity className="w-5 h-5 animate-pulse" />
        </div>
        <div>
          <h2 className="font-bold text-gray-900">Audit report compiling</h2>
          <p className="text-sm text-gray-600">Scoring crawl data and building recommendations</p>
        </div>
      </div>
      <span className="text-2xl font-bold text-blue-700">{progress}%</span>
    </div>
    <div className="h-3 bg-white rounded-full overflow-hidden border border-blue-100">
      <div className="h-full bg-blue-600 progress-slide transition-all duration-700" style={{ width: `${progress}%` }} />
    </div>
  </div>
);

const AuditReport: React.FC = () => {
  const { auditId } = useParams();
  const [expandedCategories, setExpandedCategories] = useState<string[]>(['critical']);
  const [auditData, setAuditData] = useState<AuditReportResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [shareStatus, setShareStatus] = useState('');
  const [progress, setProgress] = useState(8);

  useEffect(() => {
    if (!auditId) return;

    let stopped = false;
    let attempts = 0;
    let timer: number | undefined;
    const maxAttempts = 120;

    const load = async () => {
      try {
        const report = await api.getAuditReport(auditId);
        if (!stopped) {
          setAuditData(report);
          setError('');
          setProgress(100);
          setIsLoading(false);
        }
      } catch (err) {
        attempts += 1;
        if (attempts < maxAttempts) {
          if (!stopped) {
            setProgress((current) => Math.min(95, Math.max(current + 1, Math.round(8 + (attempts / maxAttempts) * 87))));
          }
          timer = window.setTimeout(load, 1500);
          return;
        }
        if (!stopped) setError(err instanceof Error ? err.message : 'Failed to load audit report');
      } finally {
        if (!stopped && attempts >= maxAttempts) setIsLoading(false);
      }
    };

    const progressTimer = window.setInterval(() => {
      setProgress((current) => Math.min(95, current + 1));
    }, 1200);
    load();

    return () => {
      stopped = true;
      if (timer) window.clearTimeout(timer);
      window.clearInterval(progressTimer);
    };
  }, [auditId]);

  const issueSections = [
    { severity: 'critical', issueKey: 'critical', label: 'Critical' },
    { severity: 'warning', issueKey: 'warnings', label: 'Warnings' },
    { severity: 'opportunity', issueKey: 'opportunities', label: 'Opportunities' }
  ] as const;

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => (prev.includes(category) ? prev.filter((c) => c !== category) : [...prev, category]));
  };

  const getCategoryIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertCircle className="w-5 h-5 text-red-600" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-600" />;
      case 'opportunity':
        return <Lightbulb className="w-5 h-5 text-blue-600" />;
      default:
        return null;
    }
  };

  const getCategoryColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-50 border-red-200';
      case 'warning':
        return 'bg-yellow-50 border-yellow-200';
      case 'opportunity':
        return 'bg-blue-50 border-blue-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  if (isLoading) return <AuditProgressPanel progress={progress} />;
  if (error) return <div className="card text-red-600">{error}</div>;
  if (!auditData) return <div className="card text-gray-500">Audit report not found.</div>;

  const report = auditData.report;
  const projectName = auditData.project?.name || 'Website audit';
  const projectDomain = auditData.project?.domain || 'Unknown website';
  const copyShareLink = async () => {
    await navigator.clipboard.writeText(window.location.href);
    setShareStatus('Link copied');
    window.setTimeout(() => setShareStatus(''), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="card border-blue-100 bg-blue-50">
        <div className="flex items-start justify-between gap-4">
        <div>
            <h1 className="text-2xl font-bold text-gray-900">{projectName}</h1>
            <p className="text-gray-900 font-semibold mt-1">{projectDomain}</p>
            <p className="text-sm text-gray-600 mt-1">
            Audit #{auditId} · Generated on {new Date(auditData.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="flex gap-3">
          <button onClick={copyShareLink} className="btn-secondary flex items-center gap-2">
            <Share2 className="w-4 h-4" />
            {shareStatus || 'Share'}
          </button>
          <button
            onClick={() => downloads.auditCsv(String(auditId))}
            className="btn-secondary flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
          <button
            onClick={() => openFiles.auditPdf(String(auditId))}
            className="btn-secondary flex items-center gap-2"
          >
            <Eye className="w-4 h-4" />
            Open PDF
          </button>
          <button
            onClick={() => downloads.auditPdf(String(auditId))}
            className="btn-secondary flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export PDF
          </button>
        </div>
        </div>
      </div>

      <div className="card">
        <div className="flex flex-col md:flex-row items-center gap-8">
          <div className="text-center">
            <ScoreCircle score={Math.round(report.scores.overall || 0)} size="lg" />
            <p className="mt-2 font-semibold text-gray-700">Overall Score</p>
          </div>
          <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-6">
            {Object.entries(report.scores)
              .filter(([key]) => key !== 'overall')
              .map(([key, score]) => (
                <div key={key} className="text-center">
                  <ScoreCircle score={Math.round(score)} size="sm" />
                  <p className="mt-2 text-sm font-medium text-gray-600 capitalize">{key}</p>
                </div>
              ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="card bg-red-50 border-red-200">
          <div className="flex items-center gap-3 mb-2">
            <AlertCircle className="w-6 h-6 text-red-600" />
            <h3 className="font-bold text-red-700">Critical</h3>
          </div>
          <p className="text-3xl font-bold text-red-700">{report.summary.critical_count}</p>
        </div>
        <div className="card bg-yellow-50 border-yellow-200">
          <div className="flex items-center gap-3 mb-2">
            <AlertTriangle className="w-6 h-6 text-yellow-600" />
            <h3 className="font-bold text-yellow-700">Warnings</h3>
          </div>
          <p className="text-3xl font-bold text-yellow-700">{report.summary.warning_count}</p>
        </div>
        <div className="card bg-blue-50 border-blue-200">
          <div className="flex items-center gap-3 mb-2">
            <Lightbulb className="w-6 h-6 text-blue-600" />
            <h3 className="font-bold text-blue-700">Opportunities</h3>
          </div>
          <p className="text-3xl font-bold text-blue-700">{report.summary.opportunity_count}</p>
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-bold text-gray-900">Detailed Findings</h2>

        {issueSections.map(({ severity, issueKey, label }) => (
          <div key={severity} className={`border rounded-xl overflow-hidden ${getCategoryColor(severity)}`}>
            <button onClick={() => toggleCategory(severity)} className="w-full px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                {getCategoryIcon(severity)}
                <span className="font-bold text-gray-900">{label} Issues</span>
                <span
                  className={`px-2 py-1 rounded-full text-xs font-semibold ${
                    severity === 'critical'
                      ? 'bg-red-100 text-red-700'
                      : severity === 'warning'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-blue-100 text-blue-700'
                  }`}
                >
                  {report.issues[issueKey].length}
                </span>
              </div>
              {expandedCategories.includes(severity) ? (
                <ChevronUp className="w-5 h-5 text-gray-500" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-500" />
              )}
            </button>

            {expandedCategories.includes(severity) && (
              <div className="px-6 pb-6 space-y-4">
                {report.issues[issueKey].length > 0 ? (
                  report.issues[issueKey].map((issue, idx) => <IssueCard key={idx} issue={issue} />)
                ) : (
                  <div className="text-sm text-gray-500">No issues in this category.</div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="card">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Recommended Action Plan</h2>
        <div className="space-y-4">
          {report.top_issues.length > 0 ? (
            report.top_issues.slice(0, 5).map((issue, idx) => (
              <div key={`${issue.title}-${idx}`} className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex-shrink-0 w-8 h-8 bg-brand-orange text-white rounded-full flex items-center justify-center font-bold text-sm">
                  {idx + 1}
                </div>
                <div>
                  <h3 className="font-bold text-gray-900">{issue.title}</h3>
                  <p className="text-sm text-gray-600 mt-1">{issue.recommendation}</p>
                  <div className="flex gap-2 mt-3">
                    <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-semibold">
                      Impact {issue.impact_score}
                    </span>
                    <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-semibold capitalize">
                      {issue.severity}
                    </span>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p className="text-gray-500">No action items were generated for this audit.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AuditReport;
