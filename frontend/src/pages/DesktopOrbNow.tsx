import React from 'react';
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  FileText,
  Globe,
  Monitor,
  MousePointer2,
  Search,
  Server,
  Settings,
  ShieldCheck,
} from 'lucide-react';
import PublicHeader from '../components/PublicHeader';
import '../landing/Landing.css';

type SurfaceGroup = {
  title: string;
  description: string;
  items: string[];
};

const movementIntents = [
  'ATTENTION_ACQUIRE',
  'GUIDE_TO_TARGET',
  'PRESENT_INFORMATION',
  'WAIT_WITH_PURPOSE',
  'RETURN_TO_COMPANION_POSITION',
  'INTERRUPT',
  'CELEBRATE',
  'WARN',
];

const statusCards = [
  {
    icon: Monitor,
    title: 'Movement contract',
    description: 'FieldMotion baseline, shared intent vocabulary, anti-linger doctrine, target clearance, and platform-specific renderers.',
  },
  {
    icon: Activity,
    title: 'Diagnostic surface',
    description: 'A bounded, read-only system scan covering hardware, Windows, networking, applications, security, and ORB runtime health.',
  },
  {
    icon: MousePointer2,
    title: 'Endpoint and pointer logic',
    description: 'Local endpoint discovery plus deterministic Windows UI Automation and accessibility-tree targets for verified guidance.',
  },
];

const scanIcons = [Settings, FileText, Globe, ShieldCheck, Server, Search];

const scanGroups: SurfaceGroup[] = [
  {
    title: 'System and hardware',
    description: 'Read-only machine evidence from trusted Windows and hardware interfaces.',
    items: [
      'CPU load, frequency, temperature, and throttling',
      'GPU load, VRAM, clocks, thermals, and compute processes',
      'RAM pressure, paging, and swap activity',
      'Disk capacity, SMART state, file-system warnings, and I/O latency',
      'Motherboard sensors and peripheral status where supported',
    ],
  },
  {
    title: 'Operating system',
    description: 'Health evidence for Windows, services, drivers, and selected runtime dependencies.',
    items: [
      'System and Application event logs',
      'Process table, resource use, and parent/child relationships',
      'Startup items, scheduled tasks, and Windows services',
      'Driver versions, device state, and mismatch indicators',
      'Narrow registry checks tied to a diagnosed subsystem',
    ],
  },
  {
    title: 'Network and endpoints',
    description: 'Deterministic discovery of local services and the process that owns each listener.',
    items: [
      'Interfaces, routes, gateways, and DNS servers',
      'Latency, jitter, packet loss, and DNS-resolution timing',
      'Loopback and approved local-network listeners',
      'Process-to-port association and expected health paths',
      'Firewall evidence relevant to the selected service',
    ],
  },
  {
    title: 'Applications and security',
    description: 'Evidence-based application health without treating unfamiliar software as malicious by default.',
    items: [
      'Crash reports, stack traces, versions, and missing dependencies',
      'Per-application CPU, RAM, disk, and GPU use',
      'Antivirus state, signature freshness, and quarantine summaries',
      'Executable signing and provenance for a selected process',
      'Repeated service, login, lockout, or listener failures',
    ],
  },
  {
    title: 'LLM and ORB runtime',
    description: 'Direct health checks for the local cognition, voice, motion, MCP, and Vault systems.',
    items: [
      'llama.cpp identity, launch arguments, model, context, and endpoint health',
      'CUDA detection, GPU-layer offload, VRAM allocation, and inference latency',
      'Qwen TTS, microphone, speech recognition, and voice latency',
      'Motion frame timing, dropped frames, target resolution, and anti-linger state',
      'MCP tool registration and Vault schema/manifest integrity',
    ],
  },
  {
    title: 'Research lane',
    description: 'Current external research is permitted only when tied to observed local evidence.',
    items: [
      'Official driver and Windows known-issue sources',
      'Official application release notes and bug trackers',
      'Security advisories and CVEs',
      'Hardware specifications and thermal limits',
      'llama.cpp, Qwen, CUDA, quantization, and VRAM guidance',
    ],
  },
];

const prohibited = [
  'Personal documents',
  'Email contents',
  'Browser history',
  'Passwords and credential stores',
  'Encrypted personal stores',
  'Cloud-account contents',
  'Financial records',
  'Private messages and personal media',
  'Unrelated project folders',
];

const DesktopOrbNow: React.FC = () => {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <PublicHeader theme="dark" />

      <section className="border-b border-white/10 bg-[radial-gradient(circle_at_top_left,_rgba(6,182,212,0.16),_transparent_38%),radial-gradient(circle_at_top_right,_rgba(249,115,22,0.12),_transparent_34%)] px-5 py-20 sm:px-8 lg:px-16">
        <div className="mx-auto max-w-7xl">
          <p className="text-sm font-bold uppercase tracking-[0.28em] text-cyan-300">Now // Desktop ORB Assistant</p>
          <h1 className="mt-5 max-w-5xl text-4xl font-black leading-tight sm:text-5xl lg:text-6xl">
            Movement with intent. Diagnostics without entering the personal domain.
          </h1>
          <p className="mt-6 max-w-4xl text-lg leading-8 text-slate-300">
            Orb Weaver is preparing the shared movement contract and the canonical diagnostic surface for the Desktop ORB Assistant. This page defines what the ORB may observe, how it interprets evidence, how it discovers endpoints and controls, and what it must never scan.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a className="inline-flex items-center gap-2 rounded-lg bg-orange-500 px-5 py-3 font-bold text-white hover:bg-orange-400" href="/diagnostics">
              Open Diagnostics Bay <ArrowRight className="h-4 w-4" />
            </a>
            <a className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/5 px-5 py-3 font-bold text-white hover:bg-white/10" href="/demo">
              Demonstration Station
            </a>
          </div>
        </div>
      </section>

      <section className="px-5 py-14 sm:px-8 lg:px-16">
        <div className="mx-auto grid max-w-7xl gap-5 md:grid-cols-3">
          {statusCards.map(({ icon: Icon, title, description }) => (
            <article key={title} className="rounded-2xl border border-white/10 bg-white/[0.04] p-6">
              <Icon className="h-6 w-6 text-cyan-300" />
              <h2 className="mt-4 text-xl font-bold">{title}</h2>
              <p className="mt-3 text-sm leading-6 text-slate-300">{description}</p>
              <p className="mt-5 text-xs font-bold uppercase tracking-[0.2em] text-orange-300">Prepared architecture</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-white/10 bg-white/[0.025] px-5 py-16 sm:px-8 lg:px-16">
        <div className="mx-auto max-w-7xl">
          <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr]">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.24em] text-cyan-300">Movement system</p>
              <h2 className="mt-3 text-3xl font-black">The ORB moves because it has a reason.</h2>
              <p className="mt-5 leading-7 text-slate-300">
                Cursor location is an input signal, not movement authority. The Desktop ORB and Website ORBs may use different renderers, but they should share movement intentions, trajectory rules, anti-linger behavior, target clearance, and purposeful pauses.
              </p>
              <div className="mt-6 rounded-xl border border-cyan-400/20 bg-cyan-400/5 p-5 font-mono text-sm leading-7 text-cyan-100">
                <div>maxSpeed: 0.64</div>
                <div>accel: 0.04</div>
                <div>damping: 0.983</div>
                <div>steerMul: 0.74</div>
                <div>maxAcceleration: 0.065</div>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {movementIntents.map((intent) => (
                <div key={intent} className="rounded-xl border border-white/10 bg-slate-900 px-4 py-3 font-mono text-sm text-slate-200">
                  {intent}
                </div>
              ))}
              <div className="rounded-xl border border-orange-400/20 bg-orange-400/5 p-5 sm:col-span-2">
                <strong className="text-orange-200">Locked doctrine:</strong>
                <p className="mt-2 text-sm leading-6 text-slate-300">
                  No random wandering, twitching, frantic bouncing, forced corner parking, indefinite hovering, or decorative motion. Brief pauses are allowed only when they communicate purpose. The ORB must never linger.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-5 py-16 sm:px-8 lg:px-16">
        <div className="mx-auto max-w-7xl">
          <p className="text-sm font-bold uppercase tracking-[0.24em] text-cyan-300">Canonical scan list</p>
          <h2 className="mt-3 text-3xl font-black">Observe the system. Interpret the evidence. Research only what the evidence requires.</h2>
          <div className="mt-9 grid gap-5 lg:grid-cols-2">
            {scanGroups.map((group, index) => {
              const Icon = scanIcons[index] || Activity;
              return (
                <article key={group.title} className="rounded-2xl border border-white/10 bg-white/[0.04] p-6">
                  <div className="flex items-center gap-3">
                    <Icon className="h-5 w-5 text-cyan-300" />
                    <h3 className="text-xl font-bold">{group.title}</h3>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-400">{group.description}</p>
                  <ul className="mt-5 space-y-3 text-sm leading-6 text-slate-200">
                    {group.items.map((item) => (
                      <li key={item} className="flex gap-3">
                        <span className="mt-2 h-1.5 w-1.5 flex-none rounded-full bg-orange-400" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="border-y border-white/10 bg-white/[0.025] px-5 py-16 sm:px-8 lg:px-16">
        <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-2">
          <article className="rounded-2xl border border-cyan-400/20 bg-cyan-400/5 p-7">
            <div className="flex items-center gap-3">
              <Server className="h-6 w-6 text-cyan-300" />
              <h2 className="text-2xl font-black">Endpoint discovery</h2>
            </div>
            <p className="mt-4 leading-7 text-slate-300">
              A local Desktop Scan Bridge or approved Desktop MCP service inventories loopback listeners, owning processes, executable paths, expected health routes, service identity, model identity, readiness, and latency.
            </p>
            <div className="mt-5 rounded-xl bg-slate-950/70 p-5 font-mono text-sm leading-7 text-slate-200">
              <div>port open</div>
              <div>service responding</div>
              <div>expected service responding</div>
              <div>expected capability ready</div>
              <div>normal ORB path verified end to end</div>
            </div>
            <p className="mt-4 text-sm text-slate-400">These are separate states and must never be reported as equivalent.</p>
          </article>

          <article className="rounded-2xl border border-orange-400/20 bg-orange-400/5 p-7">
            <div className="flex items-center gap-3">
              <MousePointer2 className="h-6 w-6 text-orange-300" />
              <h2 className="text-2xl font-black">Desktop pointer logic</h2>
            </div>
            <p className="mt-4 leading-7 text-slate-300">
              Pointer targets should resolve through explicit app adapters or Windows UI Automation and accessibility identity: process, window, role, automation id, accessible name, and parent context. Screenshots and raw coordinates are recovery tools, not the primary identity system.
            </p>
            <ol className="mt-5 space-y-3 text-sm leading-6 text-slate-200">
              {[
                'Verify the expected process and window.',
                'Resolve and verify the target control.',
                'Calculate target zone and clearance.',
                'Request GUIDE_TO_TARGET from movement.',
                'Point without covering the control.',
                'Click or type only when permission and the Stage Governor allow it.',
              ].map((item, index) => (
                <li key={item} className="flex gap-3">
                  <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full bg-orange-400/20 text-xs font-bold text-orange-200">{index + 1}</span>
                  <span>{item}</span>
                </li>
              ))}
            </ol>
          </article>
        </div>
      </section>

      <section className="px-5 py-16 sm:px-8 lg:px-16">
        <div className="mx-auto max-w-7xl rounded-2xl border border-red-400/20 bg-red-400/5 p-7">
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-6 w-6 text-red-300" />
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.2em] text-red-300">Hard boundary</p>
              <h2 className="mt-1 text-2xl font-black">What diagnostics must never scan</h2>
            </div>
          </div>
          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {prohibited.map((item) => (
              <div key={item} className="rounded-lg border border-red-300/10 bg-slate-950/50 px-4 py-3 text-sm text-slate-200">{item}</div>
            ))}
          </div>
          <p className="mt-6 max-w-4xl text-sm leading-6 text-slate-400">
            A separate owner-requested tool may access a personal source under its own explicit permission and purpose. That access is not part of Desktop ORB diagnostics.
          </p>
        </div>
      </section>

      <section className="border-t border-white/10 bg-black/20 px-5 py-14 sm:px-8 lg:px-16">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <BrainCircuit className="h-6 w-6 text-cyan-300" />
              <h2 className="text-2xl font-black">Next build order</h2>
            </div>
            <p className="mt-3 max-w-4xl leading-7 text-slate-300">
              Diagnostic Surface Map schema, read-only collectors, ORB runtime adapters, desktop target-map schema, shared movement/anti-linger contract, evidence UI, owner-approved actions, then evidence-bound research.
            </p>
          </div>
          <a className="inline-flex items-center justify-center gap-2 rounded-lg bg-orange-500 px-5 py-3 font-bold text-white hover:bg-orange-400" href="/signup?next=/diagnostics">
            Enter Orb Weaver <ArrowRight className="h-4 w-4" />
          </a>
        </div>
      </section>
    </main>
  );
};

export default DesktopOrbNow;
