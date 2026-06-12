import React from 'react';
import { AlertTriangle, AlertCircle, Lightbulb, ChevronRight } from 'lucide-react';

interface IssueCardProps {
  issue: {
    severity: string;
    category: string;
    title: string;
    description: string;
    affected_urls?: string[];
    recommendation: string;
    impact_score: number;
  };
}

const IssueCard: React.FC<IssueCardProps> = ({ issue }) => {
  const getIcon = () => {
    switch (issue.severity) {
      case 'critical': return <AlertCircle className="w-6 h-6 text-red-600" />;
      case 'warning': return <AlertTriangle className="w-6 h-6 text-yellow-600" />;
      case 'opportunity': return <Lightbulb className="w-6 h-6 text-blue-600" />;
      default: return <AlertCircle className="w-6 h-6 text-gray-600" />;
    }
  };

  const getClass = () => {
    switch (issue.severity) {
      case 'critical': return 'issue-critical';
      case 'warning': return 'issue-warning';
      case 'opportunity': return 'issue-opportunity';
      default: return 'border-l-4 border-gray-500 bg-gray-50 p-4 rounded-r-lg';
    }
  };

  return (
    <div className={getClass()}>
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 mt-1">
          {getIcon()}
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-bold text-gray-900">{issue.title}</h3>
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
              issue.severity === 'critical' ? 'bg-red-100 text-red-700' :
              issue.severity === 'warning' ? 'bg-yellow-100 text-yellow-700' :
              'bg-blue-100 text-blue-700'
            }`}>
              {issue.severity.toUpperCase()}
            </span>
          </div>
          <p className="text-gray-600 text-sm mb-3">{issue.description}</p>

          <div className="bg-white/60 rounded-lg p-3 mb-3">
            <p className="text-sm font-semibold text-gray-700 mb-1">Recommendation:</p>
            <p className="text-sm text-gray-600">{issue.recommendation}</p>
          </div>

          {issue.affected_urls && issue.affected_urls.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-semibold text-gray-500 mb-2">
                Affected URLs ({issue.affected_urls.length}):
              </p>
              <div className="space-y-1">
                {issue.affected_urls.slice(0, 3).map((url, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-xs text-gray-600">
                    <ChevronRight className="w-3 h-3" />
                    <span className="truncate max-w-md">{url}</span>
                  </div>
                ))}
                {issue.affected_urls.length > 3 && (
                  <p className="text-xs text-gray-400 pl-5">
                    +{issue.affected_urls.length - 3} more...
                  </p>
                )}
              </div>
            </div>
          )}

          <div className="mt-3 flex items-center gap-2">
            <span className="text-xs text-gray-500">Impact Score:</span>
            <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full ${
                  issue.impact_score >= 80 ? 'bg-red-500' :
                  issue.impact_score >= 60 ? 'bg-brand-accent' :
                  issue.impact_score >= 40 ? 'bg-yellow-500' :
                  'bg-blue-500'
                }`}
                style={{ width: `${issue.impact_score}%` }}
              />
            </div>
            <span className="text-xs font-semibold text-gray-700">{issue.impact_score}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default IssueCard;
