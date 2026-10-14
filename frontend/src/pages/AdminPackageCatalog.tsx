import React, { useEffect, useState } from 'react';
import { Check, Save, ShieldCheck } from 'lucide-react';
import { api, CustomerPackage } from '../services/api';

const AdminPackageCatalog: React.FC = () => {
  const [packages, setPackages] = useState<CustomerPackage[]>([]);
  const [drafts, setDrafts] = useState<Record<string, { price: string; purchasable: boolean; active: boolean }>>({});
  const [error, setError] = useState('');
  const [saved, setSaved] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const result = await api.adminGetCustomerPackageCatalog();
      setPackages(result.packages);
      setDrafts(Object.fromEntries(result.packages.map((item) => [item.sku, { price: item.price_cents === null ? '' : String(item.price_cents / 100), purchasable: item.purchasable, active: item.active }])));
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to load package catalog'); }
    finally { setLoading(false); }
  };

  useEffect(() => { void load(); }, []);

  const save = async (item: CustomerPackage) => {
    const draft = drafts[item.sku];
    if (!draft) return;
    const price = draft.price.trim() === '' ? null : Math.round(Number(draft.price) * 100);
    if (price !== null && (!Number.isFinite(price) || price < 0)) { setError('Enter a valid non-negative price or leave it blank for TBD.'); return; }
    if (draft.purchasable && price === null) { setError('A package must have a price before it can be purchasable.'); return; }
    setSaving(item.sku); setError(''); setSaved('');
    try {
      const result = await api.adminUpdateCustomerPackage(item.sku, { price_cents: price, currency: item.currency, purchasable: draft.purchasable, active: draft.active, sort_order: item.sort_order });
      setPackages(result.packages);
      setSaved(item.sku);
    } catch (err) { setError(err instanceof Error ? err.message : 'Package update failed'); }
    finally { setSaving(''); }
  };

  if (loading) return <div className="card text-slate-500">Loading customer package controls…</div>;
  return <div className="space-y-6">
    <section className="rounded-2xl bg-slate-950 px-6 py-7 text-white"><div className="flex items-start gap-3"><ShieldCheck className="mt-1 h-6 w-6 text-cyan-300" /><div><p className="text-xs font-black uppercase tracking-[0.16em] text-cyan-300">Admin / commercial authority</p><h1 className="mt-2 text-3xl font-black">Customer package catalog</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">Set the price and publish state for scan products and Website ORB editions. Blank prices remain TBD and are never purchasable.</p></div></div></section>
    {error && <div className="card border-red-200 bg-red-50 text-sm font-bold text-red-700">{error}</div>}
    <div className="grid gap-5">
      {packages.map((item) => { const draft = drafts[item.sku] || { price: '', purchasable: false, active: true }; return <section key={item.sku} className="card border-slate-200"><div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"><div className="max-w-2xl"><p className="text-xs font-black uppercase tracking-[0.14em] text-cyan-700">{item.category} {item.tier ? `· ${item.tier}` : ''}</p><h2 className="mt-2 text-xl font-black text-slate-950">{item.name}</h2><p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p><ul className="mt-3 grid gap-1 text-xs text-slate-500 sm:grid-cols-2">{item.features.map((feature) => <li key={feature}>• {feature}</li>)}</ul></div><div className="grid min-w-[260px] gap-3"><label className="text-sm font-bold text-slate-800">Price (USD)<input aria-label={`${item.name} price`} type="number" min="0" step="0.01" placeholder="TBD" value={draft.price} onChange={(event) => setDrafts((current) => ({ ...current, [item.sku]: { ...draft, price: event.target.value } }))} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" /></label><label className="flex items-center gap-2 text-sm font-bold text-slate-800"><input type="checkbox" checked={draft.purchasable} onChange={(event) => setDrafts((current) => ({ ...current, [item.sku]: { ...draft, purchasable: event.target.checked } }))} /> Purchasable</label><label className="flex items-center gap-2 text-sm font-bold text-slate-800"><input type="checkbox" checked={draft.active} onChange={(event) => setDrafts((current) => ({ ...current, [item.sku]: { ...draft, active: event.target.checked } }))} /> Visible on pricing page</label><button type="button" onClick={() => void save(item)} disabled={saving === item.sku} className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand-dark px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50"><Save className="h-4 w-4" />{saving === item.sku ? 'Saving…' : saved === item.sku ? 'Saved' : 'Save package'}</button></div></div>{saved === item.sku && <p className="mt-4 flex items-center gap-2 text-xs font-bold text-emerald-700"><Check className="h-4 w-4" />Catalog saved to the canonical Vault.</p>}</section>; })}
    </div>
  </div>;
};

export default AdminPackageCatalog;
