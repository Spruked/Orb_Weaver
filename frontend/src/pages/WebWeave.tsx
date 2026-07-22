import React from 'react';
import { BrainCircuit, CheckCircle, Compass, Sparkles } from 'lucide-react';

const updateScopes = [
  ['Structure and content recommendations', 'Clarify navigation, page purpose, headings, public service descriptions, product paths, contact options, and other visible guidance targets.'],
  ['Technical and scan-informed fixes', 'Use crawl and audit evidence to identify broken links, thin public pages, metadata issues, sitemap or robots concerns, and pages that need a clearer next action.'],
  ['ORB readiness refresh', 'After approved site changes, rescan the website so Site World knowledge, page context, and pointer targets reflect the current public site.'],
];

const governedAreas = [
  'Sensitive account workflows',
  'Transactional checkout actions',
  'Login and admin actions',
  'Payment or order operations',
  'Private customer data',
  'Owner-only systems',
];

const WebWeave: React.FC = () => {
  return (
    <div className="space-y-6">
      <section className="rounded-xl bg-brand-dark p-6 text-white">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-200">Site Update</p>
        <h1 className="mt-2 max-w-4xl text-3xl font-bold">Website updates guided by scan evidence</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
          Site Update uses Orb Weaver evidence to identify useful website changes, separate recommendations from
          approved work, verify the result, and refresh ORB site knowledge after the public website changes.
        </p>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <article className="card lg:col-span-2">
          <div className="flex items-center gap-3">
            <BrainCircuit className="h-5 w-5 text-brand-accent" />
            <h2 className="text-lg font-bold text-gray-900">Recommendations are not automatic changes</h2>
          </div>
          <p className="mt-4 text-sm leading-6 text-gray-600">
            Orb Weaver may identify updates from Preflight, crawl, audit, report, Site World, and pointer evidence.
            Those findings are recommendations until the owner authorizes a specific change. The page, route, expected
            result, and verification path should be clear before work is treated as approved.
          </p>
          <p className="mt-3 text-sm leading-6 text-gray-600">
            Approved updates can then be checked by rescanning or reviewing the affected public pages. The goal is to
            improve the website and keep the ORB&apos;s embodied guidance aligned with the site visitors actually see.
          </p>
        </article>

        <article className="card">
          <div className="flex items-center gap-3">
            <Sparkles className="h-5 w-5 text-brand-accent" />
            <h2 className="text-lg font-bold text-gray-900">Owner authorization</h2>
          </div>
          <p className="mt-4 text-sm leading-6 text-gray-600">
            No sensitive, transactional, account, checkout, login, or admin action should be treated as approved by
            suggestion alone. Those areas stay governed and require explicit owner control.
          </p>
        </article>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {updateScopes.map(([title, body]) => (
          <article key={title} className="card">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-50 text-brand-accent">
              <CheckCircle className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-bold text-gray-900">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-gray-600">{body}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <article className="card">
          <div className="flex items-center gap-3">
            <Compass className="h-5 w-5 text-brand-accent" />
            <h2 className="text-lg font-bold text-gray-900">Verification loop</h2>
          </div>
          <ol className="mt-4 space-y-3 text-sm leading-6 text-gray-600">
            <li><strong className="text-gray-900">1. Identify:</strong> Use scan and audit evidence to describe what was found and why it matters.</li>
            <li><strong className="text-gray-900">2. Approve:</strong> Confirm the affected page, planned change, and owner authorization before work proceeds.</li>
            <li><strong className="text-gray-900">3. Verify:</strong> Review the affected public page or route after the change.</li>
            <li><strong className="text-gray-900">4. Rescan:</strong> Run the appropriate scan again so reports, Site World knowledge, and pointer targets refresh.</li>
          </ol>
        </article>

        <article className="card border-amber-200 bg-amber-50">
          <h2 className="text-lg font-bold text-gray-900">Governed areas remain governed</h2>
          <div className="mt-4 flex flex-wrap gap-2">
            {governedAreas.map((area) => (
              <span key={area} className="rounded-full border border-amber-200 bg-white px-3 py-1.5 text-xs font-bold text-amber-800">{area}</span>
            ))}
          </div>
          <p className="mt-4 text-sm leading-6 text-gray-700">
            Site Update can identify issues around these areas, but it should not perform or authorize protected actions
            without the required owner approval and runtime policy.
          </p>
        </article>
      </section>

      <section className="card">
        <div className="flex items-center gap-3">
          <Compass className="h-5 w-5 text-brand-accent" />
          <h2 className="text-lg font-bold text-gray-900">Positioning note</h2>
        </div>
        <p className="mt-4 text-sm leading-6 text-gray-600">
          Site Update is the ORB-ready website improvement path. The website, scans, reports, Site World, and pointer
          guidance need to move together so Weaver remains a useful website consultant instead of relying on stale page
          knowledge.
        </p>
      </section>
    </div>
  );
};

export default WebWeave;
