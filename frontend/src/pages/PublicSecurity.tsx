import React, { useEffect } from 'react';
import PublicHeader from '../components/PublicHeader';

const quickAnswers = [
  {
    question: 'What can the ORB do?',
    answer:
      'It can understand page context, answer visitor questions naturally, guide attention to verified next steps, and help people finish the journeys your website was built to support.',
  },
  {
    question: 'What can it NOT do?',
    answer:
      'It cannot invent permissions, pretend a control exists, claim an action succeeded without verification, or act outside the rules enforced by the runtime control layer.',
  },
  {
    question: "Can it control my customer's computer?",
    answer:
      'No. A Website ORB operates inside the website experience. It does not take control of a visitor device, desktop, files, or operating system.',
  },
  {
    question: 'Can it click buttons automatically?',
    answer:
      'Not by default. It can guide to a verified target and explain the next step, but visitor-facing execution remains bounded by runtime permissions and approval rules.',
  },
  {
    question: 'Can it purchase things?',
    answer:
      'No. It may help a visitor understand an offer or reach the correct checkout step, but it is not allowed to complete a purchase on the visitor behalf.',
  },
  {
    question: 'Can it submit forms?',
    answer:
      'No uncontrolled submission is allowed. The system is designed so guidance and reasoning are separate from consequential execution, preserving visitor control.',
  },
];

const trustLayers = [
  {
    title: 'Control Plane',
    body:
      'The control plane owns execution. The AI can interpret, explain, and recommend, but the runtime control layer decides what tools exist, what actions are permitted, and what can actually run.',
    improves:
      'This prevents the visitor experience from drifting into unverified, improvisational behavior.',
  },
  {
    title: 'Verification',
    body:
      'Orb Weaver verifies state before claiming success. If a fact, target, or action has not been verified, the ORB must present that uncertainty honestly instead of guessing.',
    improves:
      'Visitors get guidance they can trust, and owners get a system that protects credibility.',
  },
  {
    title: 'Stage Governor',
    body:
      'The Stage Governor defines the current objective and allowed actions. The AI does not decide its own authority; it operates inside the stage rules it has been given.',
    improves:
      'This keeps recommendations aligned with the correct customer journey and prevents unsafe shortcuts.',
  },
  {
    title: 'Tool Permissions',
    body:
      'Every tool must be explicitly registered, permitted, and called with supported arguments. There are no hidden or implied tools.',
    improves:
      'Owners can understand exactly what the ORB is capable of and where its boundaries are enforced.',
  },
  {
    title: 'Pointer Verification',
    body:
      'Visual guidance is allowed only when a mapped target exists, the route matches, geometry is current, and the live target is verified.',
    improves:
      'The ORB points to real controls, not estimated locations or stale UI memory.',
  },
  {
    title: 'Visitor Always Remains in Control',
    body:
      'The architecture is designed so the ORB helps, explains, and guides without taking the website experience away from the visitor.',
    improves:
      'That preserves trust, reduces risk, and makes the system feel like a capable guide instead of an unpredictable automation layer.',
  },
];

const PublicSecurity: React.FC = () => {
  useEffect(() => {
    document.title = 'Security | ORB Weaver';
  }, []);

  return (
    <main className="min-h-screen overflow-hidden bg-slate-950 text-white">
      <PublicHeader theme="dark" />

      <div className="pointer-events-none fixed inset-0 opacity-70" aria-hidden="true">
        <div className="absolute left-1/2 top-24 h-[520px] w-[760px] -translate-x-1/2 rounded-full bg-cyan-400/10 blur-3xl" />
      </div>

      <div className="relative mx-auto w-full max-w-6xl px-6 py-10 md:px-8">
        <section className="py-10 md:py-16">
          <p className="text-sm font-semibold tracking-[0.22em] text-cyan-300">SECURITY AND TRUST</p>
          <h1 className="mt-3 max-w-4xl text-4xl font-black leading-tight md:text-6xl">
            Trust is built into the architecture, not added as a disclaimer.
          </h1>
          <p className="mt-5 max-w-3xl text-lg leading-relaxed text-slate-300">
            Orb Weaver is deliberately designed so business owners can gain the value of guided website intelligence
            without giving an AI unchecked execution authority.
          </p>
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {quickAnswers.map((item) => (
            <article key={item.question} className="rounded-2xl border border-cyan-300/20 bg-white/[0.05] p-6">
              <p className="text-sm font-bold uppercase tracking-[0.08em] text-cyan-200">{item.question}</p>
              <p className="mt-3 text-slate-200 leading-7">{item.answer}</p>
            </article>
          ))}
        </section>

        <section className="mt-12">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold tracking-[0.22em] text-cyan-300">DELIBERATE TRUST DESIGN</p>
            <h2 className="mt-3 text-3xl font-black leading-tight md:text-5xl">
              The system is separated on purpose.
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-slate-300">
              Orb Weaver separates AI reasoning from live execution so the website can be more helpful without becoming less trustworthy.
              The design goal is simple: improve visitor experience while protecting owners, visitors, and business workflows.
            </p>
          </div>

          <div className="mt-8 grid gap-4">
            {trustLayers.map((layer) => (
              <article key={layer.title} className="rounded-2xl border border-cyan-300/20 bg-slate-900/60 p-6">
                <div className="grid gap-4 md:grid-cols-[0.8fr_1.2fr]">
                  <div>
                    <h3 className="text-xl font-bold text-white">{layer.title}</h3>
                  </div>
                  <div>
                    <p className="text-slate-200 leading-7">{layer.body}</p>
                    <p className="mt-3 text-sm font-semibold uppercase tracking-[0.08em] text-slate-400">
                      Why this matters for the visitor experience
                    </p>
                    <p className="mt-2 text-slate-300 leading-7">{layer.improves}</p>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="mt-12 rounded-2xl border border-cyan-300/20 bg-cyan-950/30 p-6 md:p-8">
          <p className="text-sm font-semibold tracking-[0.22em] text-cyan-300">BOTTOM LINE</p>
          <h2 className="mt-3 text-3xl font-black leading-tight md:text-5xl">
            The ORB helps visitors move forward. The architecture makes sure it does so safely.
          </h2>
          <p className="mt-4 max-w-3xl text-lg leading-relaxed text-slate-200">
            That is not a limitation we are apologizing for. It is a deliberate design decision that prioritizes trust,
            preserves business control, and keeps the website experience useful without becoming reckless.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <a href="/how-it-works" className="rounded-lg bg-cyan-300 px-5 py-3 text-sm font-bold text-slate-950 transition hover:bg-cyan-200">
              See How It Works
            </a>
            <a href="/preflight" className="rounded-lg border border-cyan-200/30 px-5 py-3 text-sm font-bold text-cyan-100 transition hover:border-cyan-200 hover:bg-cyan-300/10">
              Run Free Preflight
            </a>
          </div>
        </section>
      </div>
    </main>
  );
};

export default PublicSecurity;