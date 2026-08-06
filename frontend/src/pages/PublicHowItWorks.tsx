import React, { useEffect } from 'react';
import PublicHeader from '../components/PublicHeader';

const lifecycleSteps = [
  'Visitor arrives',
  'Website ORB understands the page',
  'Discovers visitor objective',
  'Answers questions naturally',
  'Guides to verified next steps',
  'Visitor completes their journey',
];

const technicalLayers = [
  {
    title: 'Website understanding layer',
    improves: 'It gives visitors answers that match the page they are on, reducing confusion and backtracking.',
    detail:
      'Orb Weaver compiles page structure, key routes, and important controls so responses remain relevant to the live website context.',
  },
  {
    title: 'Intent and conversation layer',
    improves: 'It helps visitors feel understood, so they move forward instead of dropping out.',
    detail:
      'The ORB interprets the visitor objective and keeps continuity across turns to guide meaningful progress.',
  },
  {
    title: 'Verified guidance layer',
    improves: 'It prevents wrong directions and builds trust in every guided step.',
    detail:
      'Pointer mapping, LiDAR geometry, and live verification keep guidance anchored to real, available page targets.',
  },
  {
    title: 'Governance and safety layer',
    improves: 'It protects visitors and your business by ensuring only approved actions are proposed.',
    detail:
      'Stage governance and runtime controls separate recommendation from execution so permissions are enforced deterministically.',
  },
];

const PublicHowItWorks: React.FC = () => {
  useEffect(() => {
    document.title = 'How It Works | ORB Weaver';
  }, []);

  return (
    <main className="min-h-screen overflow-hidden bg-slate-950 text-white">
      <PublicHeader theme="dark" />

      <div className="pointer-events-none fixed inset-0 opacity-70" aria-hidden="true">
        <div className="absolute left-1/2 top-28 h-[520px] w-[760px] -translate-x-1/2 rounded-full bg-cyan-400/10 blur-3xl" />
      </div>

      <div className="relative mx-auto w-full max-w-6xl px-6 py-10 md:px-8">
        <section className="py-10 md:py-16">
          <p className="text-sm font-semibold tracking-[0.22em] text-cyan-300">HOW IT WORKS</p>
          <h1 className="mt-3 max-w-4xl text-4xl font-black leading-tight md:text-6xl">
            Start with the visitor experience, then the technology underneath it.
          </h1>
          <p className="mt-5 max-w-3xl text-lg leading-relaxed text-slate-300">
            Orb Weaver is designed to help visitors finish meaningful tasks on your website. The technology exists to improve
            that experience, not to distract from it.
          </p>
        </section>

        <section className="rounded-2xl border border-cyan-300/25 bg-white/[0.05] p-6 md:p-8">
          <h2 className="text-2xl font-bold text-white md:text-3xl">Visitor lifecycle</h2>
          <div className="mt-6 space-y-3">
            {lifecycleSteps.map((step, index) => (
              <div key={step}>
                <div className="rounded-xl border border-white/10 bg-slate-900/60 px-4 py-3 text-base font-semibold text-slate-100">
                  {step}
                </div>
                {index < lifecycleSteps.length - 1 && (
                  <div className="flex justify-center py-2 text-cyan-300" aria-hidden="true">
                    ↓
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        <section className="mt-10">
          <h2 className="text-2xl font-bold text-white md:text-3xl">Technology that improves the experience</h2>
          <p className="mt-3 max-w-3xl text-slate-300">
            Every technical layer has one job: make the visitor journey clearer, safer, and easier to complete.
          </p>

          <div className="mt-6 grid gap-4">
            {technicalLayers.map((layer) => (
              <article key={layer.title} className="rounded-xl border border-cyan-300/20 bg-slate-900/60 p-5">
                <h3 className="text-lg font-bold text-cyan-200">{layer.title}</h3>
                <p className="mt-2 text-sm font-semibold uppercase tracking-[0.08em] text-slate-400">How this improves the visitor experience</p>
                <p className="mt-2 text-slate-200">{layer.improves}</p>
                <p className="mt-3 text-sm text-slate-400">{layer.detail}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
};

export default PublicHowItWorks;
