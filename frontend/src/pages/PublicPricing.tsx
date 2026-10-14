import React, { useEffect, useMemo, useState } from 'react';
import { Check, HelpCircle, LockKeyhole, ArrowRight } from 'lucide-react';
import PublicHeader from '../components/PublicHeader';
import PublicFooter from '../components/PublicFooter';
import { api, CustomerPackage } from '../services/api';

const fallbackPackages: CustomerPackage[] = [
  { sku: 'scan-full-intelligence', name: 'Full Website Intelligence Scan', category: 'scan', description: 'The complete scan foundation for a customer Website ORB and decision-ready reporting.', features: ['Full report and crawl evidence', 'SEO, commercial catalog, and Dandy intelligence', 'Spatial mapping and verified target readiness'], price_cents: null, currency: 'usd', pricing_status: 'tbd', purchasable: false, active: true, sort_order: 10 },
  { sku: 'scan-seo', name: 'SEO Scan', category: 'scan', description: 'A focused search, content, technical, performance, accessibility, and security scan.', features: ['Technical SEO and indexability', 'Content and structured data review', 'Prioritized recommendations'], price_cents: null, currency: 'usd', pricing_status: 'tbd', purchasable: false, active: true, sort_order: 20 },
  { sku: 'scan-dandy-ad-data', name: 'Dandy Ad Data Scan', category: 'scan', description: 'Source-grounded promotional intelligence from public commercial website evidence.', features: ['Offers, proof points, and candidate claims', 'Target-customer signals and ad angles', 'Owner approval boundary'], price_cents: null, currency: 'usd', pricing_status: 'tbd', purchasable: false, active: true, sort_order: 30 },
  { sku: 'scan-spatial-mapping', name: 'Spatial Mapping Scan', category: 'scan', description: 'Runtime-readiness evidence for spatial movement, verified destinations, and Point/Ping guidance.', features: ['Pointer Plot Map evidence', 'Live target verification readiness', 'Unresolved-target reporting'], price_cents: null, currency: 'usd', pricing_status: 'tbd', purchasable: false, active: true, sort_order: 40 },
  { sku: 'orb-basic-website-visitor', name: 'Basic Website Visitor ORB', category: 'orb', tier: 'basic', description: 'A website-native visitor guide built from approved public site evidence and verified pathways.', features: ['Voice-first visitor interaction', 'Site-specific context', 'Basic verified navigation'], price_cents: null, currency: 'usd', pricing_status: 'tbd', purchasable: false, active: true, sort_order: 50 },
  { sku: 'orb-enhanced-website-intelligence', name: 'Enhanced Website Intelligence ORB', category: 'orb', tier: 'enhanced', description: 'A richer installable Website ORB with deeper intelligence, spatial guidance, and learning context.', features: ['Everything in Basic', 'Expanded SEO, Dandy, commercial, and spatial evidence', 'Verified-outcome learning context'], price_cents: null, currency: 'usd', pricing_status: 'tbd', purchasable: false, active: true, sort_order: 60 },
  { sku: 'orb-platinum-premium-dock-station', name: 'Platinum Website ORB w/Premium Dock Station', category: 'orb', tier: 'platinum', description: 'The complete Website ORB delivery with Premium Dock Station owner controls and deployment support.', features: ['Everything in Enhanced', 'Premium Dock Station controls', 'Expanded deployment and verification workflow'], price_cents: null, currency: 'usd', pricing_status: 'tbd', purchasable: false, active: true, sort_order: 70 },
];

const displayPrice = (item: CustomerPackage) => item.price_cents === null ? 'Pricing TBD' : new Intl.NumberFormat('en-US', { style: 'currency', currency: item.currency.toUpperCase() }).format(item.price_cents / 100);

const PackageCard: React.FC<{ item: CustomerPackage; featured?: boolean }> = ({ item, featured }) => (
  <article className={`rounded-2xl border p-6 shadow-sm ${featured ? 'border-cyan-300 bg-slate-950 text-white shadow-cyan-100' : 'border-slate-200 bg-white text-slate-950'}`} data-orb-target={`pricing-${item.sku}`}>
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className={`text-xs font-black uppercase tracking-[0.16em] ${featured ? 'text-cyan-300' : 'text-cyan-700'}`}>{item.category === 'orb' ? `${item.tier || 'Website'} ORB` : 'Scan package'}</p>
        <h2 className="mt-3 text-2xl font-black leading-tight">{item.name}</h2>
      </div>
      {item.tier === 'platinum' && <span className="rounded-full bg-amber-300 px-3 py-1 text-xs font-black text-amber-950">Premium</span>}
    </div>
    <p className={`mt-4 text-sm leading-7 ${featured ? 'text-slate-300' : 'text-slate-600'}`}>{item.description}</p>
    <p className="mt-6 text-3xl font-black">{displayPrice(item)}</p>
    <ul className={`mt-6 space-y-3 border-t pt-5 text-sm ${featured ? 'border-white/10 text-slate-200' : 'border-slate-200 text-slate-700'}`}>
      {item.features.map((feature) => <li key={feature} className="flex gap-2"><Check className="mt-0.5 h-4 w-4 shrink-0 text-cyan-500" />{feature}</li>)}
    </ul>
    <div className="mt-7 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em]">
      {item.purchasable ? <span className="text-emerald-600">Available for purchase</span> : <><HelpCircle className="h-4 w-4" /><span>Admin pricing and approval pending</span></>}
    </div>
  </article>
);

const PublicPricing: React.FC = () => {
  const [packages, setPackages] = useState<CustomerPackage[]>(fallbackPackages);
  const [error, setError] = useState('');
  useEffect(() => {
    document.title = 'Pricing & Packages | Orb Weaver';
    void api.getCustomerPackageCatalog().then((result) => setPackages(result.packages.filter((item) => item.active))).catch(() => setError('The package catalog is temporarily unavailable. Showing the planned package structure.'));
  }, []);
  const scans = useMemo(() => packages.filter((item) => item.category === 'scan'), [packages]);
  const orbs = useMemo(() => packages.filter((item) => item.category === 'orb'), [packages]);
  return <main className="min-h-screen bg-slate-50 text-slate-950"><PublicHeader />
    <section className="bg-slate-950 px-5 py-20 text-white sm:px-8 sm:py-28"><div className="mx-auto max-w-6xl"><p className="text-xs font-black uppercase tracking-[0.18em] text-cyan-300">Scan → compile → install</p><h1 className="mt-5 max-w-4xl text-5xl font-black tracking-[-0.06em] sm:text-7xl">The intelligence layer behind your Website ORB.</h1><p className="mt-7 max-w-3xl text-lg leading-8 text-slate-300">Choose the scan evidence you need, or select an installable Website ORB built from your site’s verified structure, content, commercial signals, and visitor pathways.</p><div className="mt-8 flex flex-wrap gap-3 text-sm font-bold text-slate-300"><span className="rounded-full border border-white/15 px-4 py-2">Single-Vault package</span><span className="rounded-full border border-white/15 px-4 py-2">Owner-governed</span><span className="rounded-full border border-white/15 px-4 py-2">Pricing controlled by admin</span></div></div></section>
    <section className="mx-auto max-w-6xl px-5 py-16 sm:px-8"><div className="mb-10 flex items-end justify-between gap-6"><div><p className="text-xs font-black uppercase tracking-[0.16em] text-cyan-700">Scan packages</p><h2 className="mt-3 text-4xl font-black tracking-tight">Start with evidence.</h2><p className="mt-3 max-w-2xl text-slate-600">Every scan package is preserved as customer intelligence and can become part of a later ORB build.</p></div><LockKeyhole className="hidden h-10 w-10 text-slate-300 sm:block" /></div><div className="grid gap-5 md:grid-cols-2">{scans.map((item) => <PackageCard key={item.sku} item={item} />)}</div></section>
    <section className="bg-white px-5 py-16 sm:px-8"><div className="mx-auto max-w-6xl"><p className="text-xs font-black uppercase tracking-[0.16em] text-cyan-700">Installable ORB editions</p><h2 className="mt-3 text-4xl font-black tracking-tight">Choose the visitor experience.</h2><div className="mt-10 grid gap-5 lg:grid-cols-3">{orbs.map((item, index) => <PackageCard key={item.sku} item={item} featured={index === 1} />)}</div></div></section>
    <section className="mx-auto max-w-6xl px-5 py-12 sm:px-8"><div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm leading-7 text-amber-950"><strong>Pricing is currently TBD.</strong> Packages are visible for product planning but cannot be purchased until an administrator sets and approves a price in the ORB package controls. {error}</div><a href="/founding-beta" className="mt-8 inline-flex items-center gap-2 font-bold text-cyan-800 hover:text-cyan-600">Discuss a package <ArrowRight className="h-4 w-4" /></a></section>
    <PublicFooter /></main>;
};

export default PublicPricing;
