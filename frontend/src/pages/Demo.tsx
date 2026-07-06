import React from 'react';
import { Customer } from '../services/api';

interface DemoProps {
  customer: Customer;
}

const Demo: React.FC<DemoProps> = ({ customer }) => {
  return (
    <div className="space-y-4">
      <section className="rounded-xl bg-brand-dark p-5 text-white">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-200">Demonstration Station</p>
        <h1 className="mt-2 text-3xl font-bold">ORB Weaver demonstration page</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-300">
          Signed in as {customer.email}. This station runs authenticated ORB demonstrations against the live tool dispatcher.
        </p>
      </section>

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-slate-950 shadow-sm">
        <iframe
          className="h-[calc(100vh-260px)] min-h-[720px] w-full border-0"
          src="/demonstration-station.html?embedded=1"
          title="ORB Weaver Demonstration Station"
        />
      </section>
    </div>
  );
};

export default Demo;
