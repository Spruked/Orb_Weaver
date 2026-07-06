import React from 'react';
import { Activity, ArrowRight, ShieldCheck, Store } from 'lucide-react';
import { Customer } from '../services/api';

interface DiagnosticsPlaceholderProps {
  customer: Customer;
}

const DiagnosticsPlaceholder: React.FC<DiagnosticsPlaceholderProps> = ({ customer }) => {
  return (
    <div className="space-y-6">
      <section className="rounded-xl bg-brand-dark p-6 text-white">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-200">ORB Marketplace</p>
        <h1 className="mt-2 text-3xl font-bold">Diagnostics Bay</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
          Signed in as {customer.email}. Diagnostics Bay is reserved for users running checks on ORBs they own.
        </p>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <article className="card lg:col-span-2">
          <div className="flex items-center gap-3">
            <Activity className="h-5 w-5 text-brand-accent" />
            <h2 className="text-lg font-bold text-gray-900">Owned-ORB diagnostics placeholder</h2>
          </div>
          <p className="mt-4 text-sm leading-6 text-gray-600">
            This bay will run authenticated diagnostics against a customer-owned Website ORB, Desktop ORB, Dock Station,
            voice runtime, and marketplace-installed assets. The public demonstration work now lives on the Demonstration
            Station page.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <a className="btn-primary inline-flex items-center gap-2" href="/demo">
              Open Demonstration Station <ArrowRight className="h-4 w-4" />
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
            Diagnostics require a logged-in account and an ORB ownership record before live checks are enabled.
          </p>
        </article>
      </section>
    </div>
  );
};

export default DiagnosticsPlaceholder;
