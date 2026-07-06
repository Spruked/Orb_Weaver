import React from 'react';
import { BrainCircuit, CheckCircle, Compass, Sparkles } from 'lucide-react';

const WebWeave: React.FC = () => {
  return (
    <div className="space-y-6">
      <section className="rounded-xl bg-brand-dark p-6 text-white">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-200">Web Weave</p>
        <h1 className="mt-2 max-w-4xl text-3xl font-bold">A website built for intelligence</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
          ORB AI integration gives a new business the structure, context, and guidance layer it needs to learn from you
          and with you from the first day the site goes live.
        </p>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <article className="card lg:col-span-2">
          <div className="flex items-center gap-3">
            <BrainCircuit className="h-5 w-5 text-brand-accent" />
            <h2 className="text-lg font-bold text-gray-900">Built-in AI head start</h2>
          </div>
          <p className="mt-4 text-sm leading-6 text-gray-600">
            Web Weave is the starting point for an intelligence-ready website: the pages, ORB guidance, business
            context, scan data, and customer pathways are designed to feed the ORB what it needs to understand the
            business as it grows.
          </p>
          <p className="mt-3 text-sm leading-6 text-gray-600">
            Instead of adding AI after the site is finished, the ORB is treated as part of the foundation. It can learn
            the offer, watch the site structure, follow the owner&apos;s priorities, and help shape the next useful action.
          </p>
        </article>

        <article className="card">
          <div className="flex items-center gap-3">
            <Sparkles className="h-5 w-5 text-brand-accent" />
            <h2 className="text-lg font-bold text-gray-900">Business launch layer</h2>
          </div>
          <p className="mt-4 text-sm leading-6 text-gray-600">
            The goal is to give a business a smarter beginning: site intelligence, ORB context, guided workflows, and
            AI-ready structure from the start.
          </p>
        </article>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          ['Learn the business', 'Capture services, offers, audiences, locations, and owner priorities as structured context.'],
          ['Guide the next move', 'Use ORB cognition and scans to surface what needs attention without waiting for a manual report.'],
          ['Grow with the owner', 'Keep the intelligence layer connected to new pages, marketplace tools, diagnostics, and site changes.'],
        ].map(([title, body]) => (
          <article key={title} className="card">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-50 text-brand-accent">
              <CheckCircle className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-bold text-gray-900">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-gray-600">{body}</p>
          </article>
        ))}
      </section>

      <section className="card">
        <div className="flex items-center gap-3">
          <Compass className="h-5 w-5 text-brand-accent" />
          <h2 className="text-lg font-bold text-gray-900">Positioning note</h2>
        </div>
        <p className="mt-4 text-sm leading-6 text-gray-600">
          Web Weave is not just a website package. It is the ORB-ready website path for business owners who want their
          site, scans, tools, and AI guidance to begin as one connected system.
        </p>
      </section>
    </div>
  );
};

export default WebWeave;
