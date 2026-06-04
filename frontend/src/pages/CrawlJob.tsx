import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Globe, CheckCircle, XCircle, Image, Search, Download } from 'lucide-react';
import { api, CrawledPage, CrawlJob as CrawlJobType, fileUrls } from '../services/api';

const CrawlJob: React.FC = () => {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');
  const [searchQuery, setSearchQuery] = useState('');
  const [crawlData, setCrawlData] = useState<CrawlJobType | null>(null);
  const [pages, setPages] = useState<CrawledPage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isRunningAudit, setIsRunningAudit] = useState(false);

  useEffect(() => {
    if (!jobId) return;

    let stopped = false;
    let timer: number | undefined;

    const load = async () => {
      try {
        const job = await api.getCrawlJob(jobId);
        if (stopped) return;
        setCrawlData(job);

        if (job.status === 'completed') {
          const pageResponse = await api.getCrawlPages(jobId);
          if (!stopped) setPages(pageResponse.pages);
        }

        if (job.status === 'pending' || job.status === 'running') {
          timer = window.setTimeout(load, 2000);
        }
      } catch (err) {
        if (!stopped) setError(err instanceof Error ? err.message : 'Failed to load crawl job');
      } finally {
        if (!stopped) setIsLoading(false);
      }
    };

    load();

    return () => {
      stopped = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [jobId]);

  const filteredPages = useMemo(
    () =>
      pages.filter((page) => {
        const title = page.title || '';
        return (
          page.url.toLowerCase().includes(searchQuery.toLowerCase()) ||
          title.toLowerCase().includes(searchQuery.toLowerCase())
        );
      }),
    [pages, searchQuery]
  );

  const stats = crawlData?.stats || {};
  const pagesCrawled = crawlData?.pages_crawled || pages.length || Number(stats.total_pages || 0);
  const pagesFound = crawlData?.pages_found || Number(stats.visited_urls || 0);
  const errorsCount = crawlData?.errors_count || 0;

  const getStatusColor = (status?: number | null) => {
    if (status === 200) return 'text-green-600 bg-green-50';
    if (status === 301 || status === 302) return 'text-yellow-600 bg-yellow-50';
    if (status && status >= 400) return 'text-red-600 bg-red-50';
    return 'text-gray-600 bg-gray-50';
  };

  const getLoadTimeColor = (ms?: number | null) => {
    if (!ms) return 'text-gray-600';
    if (ms < 1000) return 'text-green-600';
    if (ms < 3000) return 'text-yellow-600';
    return 'text-red-600';
  };

  const formatDuration = () => {
    if (!crawlData?.start_time || !crawlData?.end_time) return '-';
    const ms = new Date(crawlData.end_time).getTime() - new Date(crawlData.start_time).getTime();
    if (Number.isNaN(ms) || ms < 0) return '-';
    const seconds = Math.round(ms / 1000);
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  };

  const handleRunAudit = async () => {
    if (!jobId || crawlData?.status !== 'completed') return;

    setIsRunningAudit(true);
    setError('');
    try {
      const audit = await api.runAudit(jobId);
      navigate(`/audit/${audit.audit_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start audit');
    } finally {
      setIsRunningAudit(false);
    }
  };

  if (isLoading) return <div className="card text-gray-500">Loading crawl job...</div>;
  if (error) return <div className="card text-red-600">{error}</div>;
  if (!crawlData) return <div className="card text-gray-500">Crawl job not found.</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-bold text-gray-900">Crawl Job #{jobId}</h1>
            <span
              className={`px-3 py-1 rounded-full text-sm font-semibold ${
                crawlData.status === 'completed'
                  ? 'bg-green-100 text-green-700'
                  : crawlData.status === 'running' || crawlData.status === 'pending'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-red-100 text-red-700'
              }`}
            >
              {crawlData.status.toUpperCase()}
            </span>
          </div>
          <p className="text-gray-500 flex items-center gap-2">
            <Globe className="w-4 h-4" />
            Project {crawlData.project_id}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => window.open(fileUrls.crawlCsv(String(jobId)), '_blank')}
            className="btn-secondary flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
          <button
            onClick={handleRunAudit}
            disabled={crawlData.status !== 'completed' || isRunningAudit}
            className="btn-primary disabled:opacity-50"
          >
            {isRunningAudit ? 'Starting Audit...' : 'Run Audit'}
          </button>
        </div>
      </div>

      {crawlData.error && <div className="card text-red-600">{crawlData.error}</div>}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card">
          <p className="text-sm text-gray-500 mb-1">Pages Crawled</p>
          <p className="text-2xl font-bold text-gray-900">{pagesCrawled}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500 mb-1">Pages Found</p>
          <p className="text-2xl font-bold text-gray-900">{pagesFound}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500 mb-1">Errors</p>
          <p className="text-2xl font-bold text-red-600">{errorsCount}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500 mb-1">Duration</p>
          <p className="text-2xl font-bold text-gray-900">{formatDuration()}</p>
        </div>
      </div>

      <div className="border-b border-gray-200">
        <nav className="flex gap-8">
          {['overview', 'pages', 'semantic', 'entities', 'schema', 'links', 'authority', 'trends', 'gaps', 'templates', 'mobile'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-4 px-1 border-b-2 font-medium capitalize transition-colors ${
                activeTab === tab ? 'border-brand-orange text-brand-orange' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="card">
            <h3 className="font-bold text-gray-900 mb-4">Crawl Statistics</h3>
            <div className="space-y-3">
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">Average Load Time</span>
                <span className={`font-semibold ${getLoadTimeColor(Number(stats.avg_load_time || 0))}`}>
                  {stats.avg_load_time ? `${(Number(stats.avg_load_time) / 1000).toFixed(2)}s` : '-'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">SSL Enabled</span>
                <span className="font-semibold text-green-600">{Number(stats.ssl_pages || 0)}/{pagesCrawled} pages</span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">Indexable Pages</span>
                <span className="font-semibold text-green-600">{Number(stats.indexable_pages || 0)}/{pagesCrawled}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">Duplicate Content</span>
                <span className="font-semibold text-red-600">{Number(stats.duplicate_content_pages || 0)} pages</span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">Total Images</span>
                <span className="font-semibold text-gray-900">{Number(stats.total_images || 0)}</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-600">Images Missing Alt</span>
                <span className="font-semibold text-red-600">{Number(stats.images_missing_alt || 0)}</span>
              </div>
              <div className="flex justify-between py-2 border-t border-gray-100">
                <span className="text-gray-600">Schema Pages</span>
                <span className="font-semibold text-gray-900">{Number(stats.schema_pages || 0)}</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-600">Thin Semantic Pages</span>
                <span className="font-semibold text-yellow-600">{Number(stats.semantic_thin_pages || 0)}</span>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 className="font-bold text-gray-900 mb-4">Link Analysis</h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-gray-600">Internal Links</span>
                  <span className="font-semibold text-gray-900">{Number(stats.total_internal_links || 0)}</span>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-gray-600">External Links</span>
                  <span className="font-semibold text-gray-900">{Number(stats.total_external_links || 0)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'semantic' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {pages.slice(0, 20).map((page) => (
            <div key={page.url} className="card">
              <h3 className="font-bold text-gray-900 truncate">{page.title || page.url}</h3>
              <p className="text-xs text-gray-500 truncate mb-4">{page.url}</p>
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div>
                  <p className="text-xs text-gray-500">ORB Score</p>
                  <p className="font-semibold">{page.semantic_analysis?.orb_semantic_score?.overall ?? '-'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Unique Terms</p>
                  <p className="font-semibold">{page.semantic_analysis?.unique_term_ratio ?? '-'}%</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Avg Sentence</p>
                  <p className="font-semibold">{page.semantic_analysis?.avg_sentence_words ?? '-'}</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {(page.semantic_analysis?.top_terms || []).slice(0, 8).map((term) => (
                  <span key={term.term} className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                    {term.term} {term.count}
                  </span>
                ))}
              </div>
              {page.semantic_analysis?.orb_semantic_score?.reasoning_statement && (
                <p className="mt-4 text-sm text-gray-700">{page.semantic_analysis.orb_semantic_score.reasoning_statement}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {activeTab === 'entities' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {pages.slice(0, 20).map((page) => (
            <div key={page.url} className="card">
              <h3 className="font-bold text-gray-900 truncate">{page.title || page.url}</h3>
              <p className="text-xs text-gray-500 truncate mb-4">{page.url}</p>
              <div className="flex flex-wrap gap-2">
                {(page.entity_analysis?.named_entities || []).slice(0, 16).map((entity) => (
                  <span key={entity} className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">{entity}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'schema' && (
        <div className="space-y-4">
          {pages.filter((page) => (page.schema_analysis?.count || 0) > 0 || (page.schema_analysis?.invalid_count || 0) > 0).length === 0 ? (
            <div className="card text-gray-500">No schema markup found in crawled pages.</div>
          ) : (
            pages.map((page) => (
              <div key={page.url} className="card">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h3 className="font-bold text-gray-900 truncate">{page.title || page.url}</h3>
                    <p className="text-xs text-gray-500 truncate">{page.url}</p>
                  </div>
                  <span className="text-sm font-semibold text-gray-700">{page.schema_analysis?.count || 0} blocks</span>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {(page.schema_analysis?.types || []).map((type) => (
                    <span key={type} className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">{type}</span>
                  ))}
                  {(page.schema_analysis?.errors || []).map((err, idx) => (
                    <span key={idx} className="px-2 py-1 bg-red-50 text-red-700 rounded text-xs">{err}</span>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'pages' && (
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search pages..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-brand-orange"
              />
            </div>
          </div>

          {filteredPages.length === 0 ? (
            <div className="card text-gray-500">No crawled pages available.</div>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">URL</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Load Time</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Words</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Links</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Images</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Indexable</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredPages.map((page, idx) => (
                    <tr key={`${page.url}-${idx}`} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div>
                          <p className="text-sm font-medium text-gray-900 truncate max-w-xs">{page.title || '-'}</p>
                          <p className="text-xs text-gray-500 truncate max-w-xs">{page.url}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getStatusColor(page.status_code)}`}>
                          {page.status_code || '-'}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`text-sm font-medium ${getLoadTimeColor(page.load_time_ms)}`}>
                          {page.load_time_ms ? `${(page.load_time_ms / 1000).toFixed(2)}s` : '-'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">{page.word_count || 0}</td>
                      <td className="px-6 py-4 text-sm text-gray-900">{page.internal_links || 0}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-1">
                          <Image className="w-4 h-4 text-gray-400" />
                          <span className="text-sm text-gray-900">{page.images_count || 0}</span>
                          {!!page.images_without_alt && (
                            <span className="text-xs text-red-600 ml-1">({page.images_without_alt} no alt)</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {page.is_indexable ? (
                          <CheckCircle className="w-5 h-5 text-green-500" />
                        ) : (
                          <XCircle className="w-5 h-5 text-red-500" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'issues' && <div className="card text-gray-500">Run an audit to view crawl-derived issues.</div>}
      {activeTab === 'links' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card">
            <h3 className="font-bold text-gray-900 mb-4">Internal Link Graph</h3>
            <div className="space-y-3">
              <div className="flex justify-between"><span>Nodes</span><span className="font-semibold">{crawlData.internal_link_graph?.nodes?.length || 0}</span></div>
              <div className="flex justify-between"><span>Edges</span><span className="font-semibold">{crawlData.internal_link_graph?.edges?.length || 0}</span></div>
              <div className="flex justify-between"><span>Potential Orphans</span><span className="font-semibold text-yellow-600">{crawlData.internal_link_graph?.orphan_candidates?.length || 0}</span></div>
            </div>
          </div>
          <div className="card">
            <h3 className="font-bold text-gray-900 mb-4">Potential Orphan Pages</h3>
            <div className="space-y-2">
              {(crawlData.internal_link_graph?.orphan_candidates || []).slice(0, 15).map((node) => (
                <p key={node.url} className="text-sm text-gray-700 truncate">{node.url}</p>
              ))}
              {(crawlData.internal_link_graph?.orphan_candidates || []).length === 0 && <p className="text-gray-500">No orphan candidates detected.</p>}
            </div>
          </div>
        </div>
      )}
      {activeTab === 'authority' && (
        <div className="space-y-6">
          {(crawlData.authority_flow?.insights || []).map((insight) => <div key={insight} className="card text-gray-800">{insight}</div>)}
          <div className="card">
            <h3 className="font-bold text-gray-900 mb-4">Authority Segments</h3>
            <div className="space-y-2">
              {Object.entries(crawlData.authority_flow?.segments || {}).map(([segment, data]) => (
                <div key={segment} className="flex justify-between py-2 border-b border-gray-100">
                  <span className="capitalize">{segment}</span>
                  <span className="font-semibold">{data.avg_authority} authority / {data.pages} pages</span>
                </div>
              ))}
            </div>
          </div>
          <div className="card">
            <h3 className="font-bold text-gray-900 mb-4">Top Authority Pages</h3>
            <div className="space-y-2">
              {(crawlData.authority_flow?.pages || []).slice(0, 15).map((page) => (
                <div key={String(page.url)} className="flex justify-between gap-4 py-2 border-b border-gray-100">
                  <span className="truncate">{String(page.url)}</span>
                  <span className="font-semibold">{String(page.authority)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      {activeTab === 'trends' && (
        <div className="card">
          <h3 className="font-bold text-gray-900 mb-4">Historical Trend Model</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(crawlData.trend_model?.metrics || {}).map(([metric, model]) => (
              <div key={metric} className="border border-gray-100 rounded-lg p-4">
                <p className="font-semibold capitalize">{metric.replace(/_/g, ' ')}</p>
                <p className="text-sm text-gray-600">Rolling avg {model.rolling_average} · Expected next month {model.expected_next_month}</p>
                <p className={`text-sm ${model.anomaly ? 'text-red-600' : 'text-gray-500'}`}>{model.anomaly ? 'Anomaly detected' : 'No anomaly'}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {activeTab === 'gaps' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[
            ['Missing Topics', crawlData.competitor_gap?.missing_topics || []],
            ['Missing Entities', crawlData.competitor_gap?.missing_entities || []],
            ['Missing Questions', crawlData.competitor_gap?.missing_questions || []],
            ['Missing Schema Types', crawlData.competitor_gap?.missing_schema_types || []],
            ['Missing Link Hubs', crawlData.competitor_gap?.missing_internal_link_hubs || []]
          ].map(([label, items]) => (
            <div key={String(label)} className="card">
              <h3 className="font-bold text-gray-900 mb-4">{String(label)}</h3>
              <div className="flex flex-wrap gap-2">
                {(items as string[]).length ? (items as string[]).map((item) => (
                  <span key={item} className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">{item}</span>
                )) : <p className="text-gray-500">No gaps detected.</p>}
              </div>
            </div>
          ))}
        </div>
      )}
      {activeTab === 'templates' && (
        <div className="space-y-4">
          {(crawlData.template_detection?.repeated_layouts || []).length === 0 ? (
            <div className="card text-gray-500">No repeated template clusters detected.</div>
          ) : (
            (crawlData.template_detection?.repeated_layouts || []).map((group) => (
              <div key={group.signature} className="card">
                <h3 className="font-bold text-gray-900">{group.page_count} pages · {group.duplicate_text_probability}% duplicate probability</h3>
                <p className="text-sm text-gray-600 mt-1">{group.orb_statement}</p>
                <div className="mt-3 space-y-1">
                  {group.pages.slice(0, 8).map((url) => <p key={url} className="text-xs text-gray-500 truncate">{url}</p>)}
                </div>
              </div>
            ))
          )}
        </div>
      )}
      {activeTab === 'mobile' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {pages.slice(0, 20).map((page) => (
            <div key={page.url} className="card">
              <h3 className="font-bold text-gray-900 truncate">{page.title || page.url}</h3>
              <p className="text-xs text-gray-500 truncate mb-4">{page.url}</p>
              <div className="grid grid-cols-2 gap-3">
                <div><p className="text-xs text-gray-500">Score</p><p className="font-semibold">{page.mobile_ux_analysis?.score ?? '-'}</p></div>
                <div><p className="text-xs text-gray-500">Viewport</p><p className="font-semibold">{page.mobile_ux_analysis?.viewport_scaling || '-'}</p></div>
                <div><p className="text-xs text-gray-500">Small Taps</p><p className="font-semibold">{page.mobile_ux_analysis?.small_tap_targets ?? 0}</p></div>
                <div><p className="text-xs text-gray-500">CLS Risk</p><p className="font-semibold">{page.mobile_ux_analysis?.mobile_cls_risk_elements ?? 0}</p></div>
              </div>
            </div>
          ))}
        </div>
      )}
      {activeTab === 'history' && (
        <div className="card">
          <h3 className="font-bold text-gray-900 mb-4">Historical Delta</h3>
          {!crawlData.historical?.has_previous ? (
            <p className="text-gray-500">No previous completed crawl exists for this project.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {Object.entries(crawlData.historical.deltas || {}).map(([key, value]) => (
                <div key={key} className="flex justify-between py-2 border-b border-gray-100">
                  <span className="text-gray-600 capitalize">{key.replace(/_/g, ' ')}</span>
                  <span className={`font-semibold ${value > 0 ? 'text-blue-600' : value < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                    {value > 0 ? '+' : ''}{Number(value).toFixed(key.includes('load_time') ? 1 : 0)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {activeTab === 'competitors' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {(crawlData.competitors || []).length === 0 ? (
            <div className="card text-gray-500">No competitor domains were supplied for this crawl.</div>
          ) : (
            (crawlData.competitors || []).map((competitor) => (
              <div key={competitor.domain} className="card">
                <h3 className="font-bold text-gray-900 mb-1">{competitor.domain}</h3>
                {competitor.error ? (
                  <p className="text-sm text-red-600">{competitor.error}</p>
                ) : (
                  <>
                    <div className="grid grid-cols-3 gap-3 my-4">
                      <div><p className="text-xs text-gray-500">Pages</p><p className="font-semibold">{Number(competitor.stats?.total_pages || 0)}</p></div>
                      <div><p className="text-xs text-gray-500">Schema</p><p className="font-semibold">{Number(competitor.stats?.schema_pages || 0)}</p></div>
                      <div><p className="text-xs text-gray-500">Internal</p><p className="font-semibold">{Number(competitor.stats?.total_internal_links || 0)}</p></div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(competitor.top_terms || []).slice(0, 8).map((term) => (
                        <span key={term.term} className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">{term.term} {term.count}</span>
                      ))}
                    </div>
                  </>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default CrawlJob;
