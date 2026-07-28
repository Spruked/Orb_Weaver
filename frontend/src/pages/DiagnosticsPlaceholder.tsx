import React from 'react';
import { Activity, ArrowRight, Monitor, ShieldCheck, Store } from 'lucide-react';
import { Customer } from '../services/api';

interface DiagnosticsPlaceholderProps {
  customer: Customer;
}

const DiagnosticsPlaceholder: React.FC<DiagnosticsPlaceholderProps> = ({ customer }) => {
  return (
    <div className="space-y-6">
      <section className="rounded-xl bg-brand-dark p-6 text-white">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-200">Desktop ORB Assistant</p>
        <h1 className="mt-2 text-3xl font-bold">Diagnostics Bay</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
          Signed in as {customer.email}. This authenticated bay is the future live control surface for ORBs the owner is permitted to diagnose.
        </p>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <article className="card lg:col-span-2">
          <div className="flex items-center gap-3">
            <Activity className="h-5 w-5 text-brand-accent" />
            <h2 className="text-lg font-bold text-gray-900">Read-only diagnostic pipeline</h2>
          </div>
          <p className="mt-4 text-sm leading-6 text-gray-600">
            The first release will collect system-domain evidence for hardware, Windows, networking, applications, security posture, local endpoints, and ORB runtime health. It will correlate evidence before presenting a diagnosis and will keep personal documents, email, browser history, credentials, cloud contents, and financial data outside the diagnostic scan surface.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <a className="btn-primary inline-flex items-center gap-2" href="/now/desktop-orb">
              Desktop ORB Now <Monitor className="h-4 w-4" />
            </a>
            <a className="btn-secondary inline-flex items-center gap-2" href="/demo">
              Demonstration Station <ArrowRight className="h-4 w-4" />
            </a>
            <a className="btn-secondary inline-flex items-center gap-2" href="/marketplace">
              Marketplace <Store className="h-4 w-4" />
            </a>
          </div>
        </article>

        <article className="card">
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-brand-accent" />
            <h2 className="text-lg font-bold text-gray-900">Access rule</h2>
          </div>
          <p className="mt-4 text-sm leading-6 text-gray-600">
            Live diagnostics require a logged-in account, an ORB ownership or owner/admin authority record, explicit scan scope, and an approved local Desktop Scan Bridge or MCP connection.
          </p>
        </article>
      </section>
    </div>
  );
};

export default DiagnosticsPlaceholder;
