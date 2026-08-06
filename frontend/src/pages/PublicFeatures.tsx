import React, { useEffect } from 'react';
import PublicHeader from '../components/PublicHeader';

type FeatureBlock = {
  title: string;
  problem: string;
  why: string;
  difference: string;
};

const featureBlocks: FeatureBlock[] = [
  {
    title: 'Reduce Visitor Confusion',
    problem: 'Visitors cannot quickly find the right page, action, or path.',
    why: 'Confusion increases exits and lowers conversion intent before visitors even engage.',
    difference: 'Orb Weaver uses page-aware context to guide visitors with relevant, situational responses instead of generic prompts.',
  },
  {
    title: 'Guide Visitors Naturally',
    problem: 'Static websites force people to self-navigate complex journeys.',
    why: 'When guidance feels robotic, visitors disengage instead of progressing.',
    difference: 'Orb Weaver keeps conversational continuity and helps visitors move forward through natural dialogue.',
  },
  {
    title: 'Verified Website Guidance',
    problem: 'Many assistants suggest steps that are outdated or unavailable.',
    why: 'Incorrect guidance breaks trust and increases abandonment.',
    difference: 'Orb Weaver validates targets and actions against live website state before guidance is delivered.',
  },
  {
    title: 'Visual Point and Ping',
    problem: 'Text-only instructions are slow when users need precise direction.',
    why: 'The longer it takes to locate a control, the more likely users are to leave.',
    difference: 'Orb Weaver can visually guide to verified page controls to reduce hesitation and navigation friction.',
  },
  {
    title: 'Conversation That Understands Context',
    problem: 'Disconnected answers force visitors to repeat themselves.',
    why: 'Repeated clarification creates fatigue and weakens confidence in the experience.',
    difference: 'Orb Weaver carries objective, context, and prior answers across turns to maintain momentum.',
  },
  {
    title: 'Safer AI Through Verification',
    problem: 'Unbounded assistants can overstate certainty or propose unsafe actions.',
    why: 'Safety and trust are mandatory for customer-facing workflows.',
    difference: 'Orb Weaver separates recommendation from execution and applies verification plus governance before action.',
  },
  {
    title: 'Continuous Learning',
    problem: 'Website support quality stagnates when systems do not learn from real outcomes.',
    why: 'Without learning, recurring customer friction remains unresolved.',
    difference: 'Orb Weaver records verified outcomes and incorporates approved learnings to improve guidance quality over time.',
  },
  {
    title: 'Website Intelligence',
    problem: 'Most systems do not truly understand the website they are guiding on.',
    why: 'Low website understanding leads to shallow assistance and missed conversions.',
    difference: 'Orb Weaver compiles site structure, controls, and pathways into a working website intelligence model for grounded assistance.',
  },
];

const PublicFeatures: React.FC = () => {
  useEffect(() => {
    document.title = 'Features | ORB Weaver';
  }, []);

  return (
    <main className="min-h-screen overflow-hidden bg-slate-950 text-white">
      <PublicHeader theme="dark" />

      <div className="pointer-events-none fixed inset-0 opacity-70" aria-hidden="true">
        <div className="absolute left-1/2 top-24 h-[520px] w-[760px] -translate-x-1/2 rounded-full bg-cyan-400/10 blur-3xl" />
      </div>

      <div className="relative mx-auto w-full max-w-6xl px-6 py-10 md:px-8">
        <section className="py-10 md:py-16">
          <p className="text-sm font-semibold tracking-[0.22em] text-cyan-300">FEATURES BY BUSINESS OUTCOME</p>
          <h1 className="mt-3 max-w-4xl text-4xl font-black leading-tight md:text-6xl">
            Customer outcomes first. Technology where it matters.
          </h1>
          <p className="mt-5 max-w-3xl text-lg leading-relaxed text-slate-300">
            Orb Weaver features are organized around business impact: reducing friction, improving journey completion,
            and creating a more trustworthy website experience.
          </p>
        </section>

        <section className="grid gap-5">
          {featureBlocks.map((item) => (
            <article key={item.title} className="rounded-2xl border border-cyan-300/20 bg-white/[0.05] p-6 md:p-7">
              <h2 className="text-2xl font-bold text-white">{item.title}</h2>

              <div className="mt-5 grid gap-4 md:grid-cols-3">
                <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-slate-400">What problem does this solve?</p>
                  <p className="mt-2 text-slate-200">{item.problem}</p>
                </div>

                <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4">
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-slate-400">Why does it matter?</p>
                  <p className="mt-2 text-slate-200">{item.why}</p>
                </div>

                <div className="rounded-xl border border-cyan-300/25 bg-cyan-950/30 p-4">
                  <p className="text-xs font-bold uppercase tracking-[0.1em] text-cyan-200">How is Orb Weaver different?</p>
                  <p className="mt-2 text-slate-100">{item.difference}</p>
                </div>
              </div>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
};

export default PublicFeatures;
