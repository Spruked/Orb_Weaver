import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, CreditCard, FileText, Receipt, Wallet } from 'lucide-react';
import { api, AccountWorkspaceSummary, Customer } from '../services/api';

interface AccountProps {
  customer: Customer;
  onLogout: () => void;
}

const Account: React.FC<AccountProps> = ({ customer, onLogout }) => {
  const [workspace, setWorkspace] = useState<AccountWorkspaceSummary | null>(null);
  const [workspaceError, setWorkspaceError] = useState('');

  useEffect(() => {
    let stopped = false;
    const loadWorkspace = async () => {
      try {
        const summary = await api.getAccountWorkspaceSummary();
        if (!stopped) setWorkspace(summary);
      } catch (err) {
        if (!stopped) setWorkspaceError(err instanceof Error ? err.message : 'Unable to load workspace scan status');
      }
    };
    void loadWorkspace();
    return () => { stopped = true; };
  }, []);

  const ledger = workspace?.financial_ledger;
  const currentYear = ledger?.current_year || new Date().getFullYear();
  const currentYearTotals = ledger?.yearly_totals.find((entry) => entry.year === currentYear);
  const money = (cents: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(cents / 100);
  const date = (value?: string | null) => value ? new Date(value).toLocaleDateString() : '—';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Account</h1>
        <p className="text-gray-500 mt-1">Financial ledger, prepaid scan usage, workspace status, and purchase history</p>
      </div>

      <section className="rounded-2xl bg-slate-950 p-6 text-white shadow-lg">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-300">{currentYear} account summary</p>
            <h2 className="mt-2 text-2xl font-extrabold">Your financial and scan-usage ledger</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">Paid purchases, open charges, scan usage, and recorded prepaid entitlements stay visible in one place.</p>
          </div>
          <Link to="/scan-center" className="inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-300 px-4 py-2.5 text-sm font-extrabold text-slate-950 hover:bg-cyan-200">Return to Scan Center <ArrowRight className="h-4 w-4" /></Link>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {[
            ['Paid this year', money(ledger?.paid_this_year_cents || 0)],
            ['Current outstanding balance', money(ledger?.outstanding_balance_cents || 0)],
            ['Prepaid scan credits / bundles', ledger?.prepaid_entitlements_recorded ? `${ledger.prepaid_bundles_active} active` : 'None recorded'],
            ['Scans purchased this year', String(ledger?.scans_purchased_this_year || 0)],
            ['Next invoice / open charges', ledger?.open_order_count ? `${ledger.open_order_count} open` : 'None'],
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl border border-white/10 bg-white/[0.06] p-4">
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-slate-400">{label}</p>
              <p className="mt-2 text-xl font-black text-white">{value}</p>
            </div>
          ))}
        </div>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          {(ledger?.outstanding_balance_cents || 0) > 0 ? (
            <button className="rounded-lg bg-brand-orange px-4 py-2.5 text-sm font-extrabold text-slate-950 hover:bg-amber-300">Pay Now — {money(ledger?.outstanding_balance_cents || 0)}</button>
          ) : <span className="inline-flex items-center gap-2 rounded-lg border border-emerald-300/30 bg-emerald-400/10 px-4 py-2.5 text-sm font-bold text-emerald-200"><Wallet className="h-4 w-4" /> Account Paid in Full</span>}
          {!ledger?.prepaid_entitlements_recorded && <span className="text-xs text-slate-400">Prepaid entitlements will appear here when a bundle is recorded.</span>}
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="card">
          <div className="flex flex-col gap-3 border-b border-gray-100 pb-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-gray-500">Running yearly total</p>
              <h2 className="mt-1 text-xl font-extrabold text-gray-900">{currentYear} Year-to-Date</h2>
            </div>
            <div className="flex gap-2">
              {(ledger?.available_years || []).filter((year) => year !== currentYear).slice(0, 2).map((year) => <button key={year} className="rounded-lg border border-gray-200 px-3 py-2 text-xs font-bold text-gray-600 hover:bg-gray-50">View {year}</button>)}
            </div>
          </div>
          <dl className="mt-4 space-y-3 text-sm">
            {[
              ['Full Site Scans', currentYearTotals?.full_site_scans || 0],
              ['Exact Page Scans', currentYearTotals?.exact_page_scans || 0],
              ['Changed Page Scans', currentYearTotals?.changed_page_scans || 0],
              ['Section Scans', currentYearTotals?.section_scans || 0],
              ['Website Scan Bundles', currentYearTotals?.scan_bundles || 0],
              ['Other services', currentYearTotals?.other_services || 0],
            ].map(([label, cents]) => <div key={label} className="flex justify-between gap-4"><dt className="text-gray-500">{label}</dt><dd className="font-bold text-gray-900">{money(Number(cents))}</dd></div>)}
            <div className="flex justify-between gap-4 border-t border-gray-200 pt-3 text-base"><dt className="font-extrabold text-gray-900">Total Paid</dt><dd className="font-black text-brand-blue">{money(currentYearTotals?.total_paid || 0)}</dd></div>
          </dl>
        </div>

        <div className="card">
          <div className="flex items-center gap-3"><Receipt className="h-5 w-5 text-brand-accent" /><h2 className="text-xl font-extrabold text-gray-900">Current Invoice</h2></div>
          <dl className="mt-5 space-y-3 text-sm">
            <div className="flex justify-between gap-4"><dt className="text-gray-500">Invoice #</dt><dd className="font-bold text-gray-900">{ledger?.current_invoice.invoice_number || 'Not issued'}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-gray-500">Charges</dt><dd className="font-bold text-gray-900">{money(ledger?.current_invoice.charges_cents || 0)}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-gray-500">Credits</dt><dd className="font-bold text-gray-900">{money(ledger?.current_invoice.credits_cents || 0)}</dd></div>
            <div className="flex justify-between gap-4 border-t border-gray-100 pt-3"><dt className="font-extrabold text-gray-900">Amount due</dt><dd className="font-black text-gray-900">{money(ledger?.current_invoice.amount_due_cents || 0)}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-gray-500">Due date</dt><dd className="font-bold text-gray-900">{ledger?.current_invoice.due_date || '—'}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-gray-500">Status</dt><dd className="font-bold text-emerald-700">{ledger?.current_invoice.status || 'Paid'}</dd></div>
          </dl>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="card">
          <div className="flex items-center gap-3"><CreditCard className="h-5 w-5 text-brand-accent" /><h2 className="text-xl font-extrabold text-gray-900">Available to Run</h2></div>
          <div className="mt-4 space-y-3 text-sm">
            {[
              ['Exact Page scans remaining', ledger?.available_to_run.exact_pages],
              ['Changed Page scans remaining', ledger?.available_to_run.changed_pages],
              ['Full Site scans prepaid', ledger?.available_to_run.full_site_scans],
              ['Section scans remaining', ledger?.available_to_run.sections],
            ].map(([label, value]) => <div key={label} className="flex justify-between gap-4 border-b border-gray-100 pb-2"><span className="text-gray-500">{label}</span><strong className="text-gray-900">{value == null ? 'Not recorded' : value}</strong></div>)}
          </div>
          <Link to="/scan-center" className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-brand-blue hover:text-brand-accent">Return to Scan Center <ArrowRight className="h-4 w-4" /></Link>
        </div>

        <div className="card">
          <div className="flex items-center gap-3"><FileText className="h-5 w-5 text-brand-accent" /><h2 className="text-xl font-extrabold text-gray-900">Purchase detail</h2></div>
          {ledger?.purchases.length ? <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[650px] text-left text-sm"><thead className="border-b border-gray-200 text-xs uppercase tracking-[0.08em] text-gray-500"><tr><th className="pb-3 pr-3">Date</th><th className="pb-3 pr-3">Purchase</th><th className="pb-3 pr-3">Quantity</th><th className="pb-3 pr-3">Rate</th><th className="pb-3 pr-3">Total</th><th className="pb-3">Status</th></tr></thead><tbody className="divide-y divide-gray-100">{ledger.purchases.map((purchase) => <tr key={purchase.id}><td className="py-3 pr-3 text-gray-500">{date(purchase.date)}</td><td className="py-3 pr-3 font-bold text-gray-900">{purchase.purchase}</td><td className="py-3 pr-3 text-gray-600">{purchase.quantity}</td><td className="py-3 pr-3 text-gray-600">{money(purchase.rate_cents)}</td><td className="py-3 pr-3 font-bold text-gray-900">{money(purchase.total_cents)}</td><td className="py-3 font-bold text-emerald-700">{purchase.status}</td></tr>)}</tbody></table></div> : <p className="mt-4 text-sm text-gray-500">No paid purchases are recorded yet.</p>}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="card">
          <p className="text-sm text-gray-500">Latest workspace</p>
          <p className="mt-1 font-bold text-gray-900">{workspace?.project?.name || 'No workspace yet'}</p>
          <p className="mt-1 text-sm text-gray-600">{workspace?.project?.domain || '-'}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">Latest crawl</p>
          <p className="mt-1 font-bold capitalize text-gray-900">{workspace?.latest_crawl?.status || 'Not started'}</p>
          <p className="mt-1 text-sm text-gray-600">{workspace?.latest_crawl ? `${workspace.latest_crawl.pages_crawled || 0} pages processed` : '-'}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">Latest audit</p>
          <p className="mt-1 font-bold text-gray-900">{workspace?.latest_audit?.score != null ? `${workspace.latest_audit.score}/100` : 'Not run'}</p>
          <p className="mt-1 text-sm text-gray-600">{workspace?.latest_audit?.created_at ? new Date(workspace.latest_audit.created_at).toLocaleString() : '-'}</p>
        </div>
      </section>
      {workspaceError && <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">{workspaceError}</div>}

    <div className="card max-w-4xl">
      <div className="mb-6 border-b border-gray-100 pb-5">
        <p className="text-sm text-gray-500">Business Account</p>
        <h2 className="text-2xl font-bold text-gray-900 mt-1">{customer.business_name}</h2>
        <p className="text-sm text-gray-600 mt-1">{customer.email}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <p className="text-sm text-gray-500">Customer ID</p>
          <p className="font-semibold text-gray-900">{customer.id}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Full Name</p>
          <p className="font-semibold text-gray-900">{customer.full_name || '-'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Business</p>
          <p className="font-semibold text-gray-900">{customer.business_name}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Company</p>
          <p className="font-semibold text-gray-900">{customer.company_name || '-'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Email</p>
          <p className="font-semibold text-gray-900">{customer.email}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Contact</p>
          <p className="font-semibold text-gray-900">{customer.contact_name || '-'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Phone</p>
          <p className="font-semibold text-gray-900">{customer.phone || '-'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Address</p>
          <p className="font-semibold text-gray-900">
            {[customer.address_line1, customer.address_line2, customer.city, customer.state, customer.postal_code, customer.country]
              .filter(Boolean)
              .join(', ') || '-'}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Business Phone</p>
          <p className="font-semibold text-gray-900">{customer.business_phone || '-'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Business Address</p>
          <p className="font-semibold text-gray-900">
            {[
              customer.business_address_line1,
              customer.business_address_line2,
              customer.business_city,
              customer.business_state,
              customer.business_postal_code,
              customer.business_country,
            ]
              .filter(Boolean)
              .join(', ') || '-'}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Tax ID</p>
          <p className="font-semibold text-gray-900">{customer.tax_id || '-'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Admin</p>
          <p className="font-semibold text-gray-900">{customer.is_admin ? 'Yes' : 'No'}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Status</p>
          <p className="font-semibold text-gray-900 capitalize">{customer.status}</p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Created</p>
          <p className="font-semibold text-gray-900">
            {customer.created_at ? new Date(customer.created_at).toLocaleString() : '-'}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Updated</p>
          <p className="font-semibold text-gray-900">
            {customer.updated_at ? new Date(customer.updated_at).toLocaleString() : '-'}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500">Last Login</p>
          <p className="font-semibold text-gray-900">
            {customer.last_login_at ? new Date(customer.last_login_at).toLocaleString() : '-'}
          </p>
        </div>
      </div>

      <button onClick={onLogout} className="mt-8 btn-secondary">
        Logout
      </button>
    </div>
  </div>
  );
};

export default Account;
