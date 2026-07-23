import React from 'react';
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { CrawlJob } from '../services/api';

const LABELS: Record<string, string> = {
  total_pages: 'Pages crawled',
  avg_load_time: 'Average load time',
  indexable_pages: 'Indexable pages',
  duplicate_content_pages: 'Duplicate content pages',
  images_missing_alt: 'Images missing alt text',
  schema_pages: 'Schema pages',
  schema_errors: 'Schema errors',
  semantic_thin_pages: 'Thin semantic pages',
  internal_link_edges: 'Internal link edges',
};

const goodWhenPositive = new Set(['total_pages', 'indexable_pages', 'schema_pages', 'internal_link_edges']);
const goodWhenNegative = new Set(['avg_load_time', 'duplicate_content_pages', 'images_missing_alt', 'schema_errors', 'semantic_thin_pages']);

const toneFor = (key: string, value: number) => {
  if (value === 0) return 'text-slate-600';
  if ((value > 0 && goodWhenPositive.has(key)) || (value < 0 && goodWhenNegative.has(key))) return 'text-emerald-700';
  if ((value < 0 && goodWhenPositive.has(key)) || (value > 0 && goodWhenNegative.has(key))) return 'text-red-700';
  return 'text-blue-700';
};

const formatValue = (key: string, value: number) => {
  const prefix = value > 0 ? '+' : '';
  if (key.includes('load_time')) return `${prefix}${value.toFixed(1)} ms`;
  return `${prefix}${value.toFixed(0)}`;
};

const ChangeIcon: React.FC<{ value: number }> = ({ value }) => {
  if (value > 0) return <ArrowUpRight className="h-4 w-4" />;
  if (value < 0) return <ArrowDownRight className="h-4 w-4" />;
  return <Minus className="h-4 w-4" />;
};

const CrawlChangeSummary: React.FC<{ crawl?: CrawlJob | null; title?: string }> = ({ crawl, title = 'What changed since the previous crawl' }) => {
  const deltas = crawl?.historical?.deltas || {};
  const entries = Object.entries(deltas)
    .map(([key, value]) => [key, Number(value)] as const)
    .filter(([, value]) => Number.isFinite(value));

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-[0.12em] text-brand-accent">Recrawl differences</p>
          <h2 className="mt-1 text-lg font-bold text-slate-950">{title}</h2>
        </div>
        {crawl?.id && <span className="rounded-full border border-slate-200 px-3 py-1 text-xs font-bold text-slate-600">Crawl #{crawl.id}</span>}
      </div>

      {!crawl ? (
        <p className="mt-3 text-sm text-slate-500">No crawl has been recorded for this workspace yet.</p>
      ) : !crawl.historical?.has_previous ? (
        <p className="mt-3 text-sm text-slate-500">This is the first completed crawl for the project, so there is no previous scan to compare.</p>
      ) : entries.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">No measured differences were found against the previous completed crawl.</p>
      ) : (
        <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {entries.map(([key, value]) => (
            <div key={key} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5">
              <div className={`flex items-center justify-between gap-3 font-bold ${toneFor(key, value)}`}>
                <span className="text-sm text-slate-800">{LABELS[key] || key.replace(/_/g, ' ')}</span>
                <span className="inline-flex items-center gap-1 text-sm">
                  <ChangeIcon value={value} />
                  {formatValue(key, value)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
};

export default CrawlChangeSummary;
