import React, { ReactNode, useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Globe,
  Search,
  BarChart3,
  Settings,
  FileText,
  User,
  ShoppingCart,
  Shield,
  Store,
  Activity,
  BrainCircuit,
  ChevronLeft,
  Mail,
  Menu,
  Monitor,
  ScanLine,
} from 'lucide-react';
import { Customer } from '../services/api';
import { marketplaceUrl } from '../services/marketplaceUrl';

const bannerLogo = '/orbweaver1600.png';
const squareLogo = '/orbweaverlogo1024.png';

interface LayoutProps {
  children: ReactNode;
  customer: Customer;
}

const Layout: React.FC<LayoutProps> = ({ children, customer }) => {
  const location = useLocation();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard', hover: 'hover:border-cyan-400/60 hover:bg-cyan-400/15 hover:text-cyan-100' },
    { path: '/projects', icon: Globe, label: 'Projects', hover: 'hover:border-blue-400/60 hover:bg-blue-400/15 hover:text-blue-100' },
    { path: '/scan-center', icon: ScanLine, label: 'Scan Center', hover: 'hover:border-emerald-400/60 hover:bg-emerald-400/15 hover:text-emerald-100' },
    { path: '/crawl', icon: Search, label: 'Crawl Jobs', hover: 'hover:border-violet-400/60 hover:bg-violet-400/15 hover:text-violet-100' },
    { path: '/ga4', icon: BarChart3, label: 'GA4 Analytics', hover: 'hover:border-sky-400/60 hover:bg-sky-400/15 hover:text-sky-100' },
    { path: '/reports', icon: FileText, label: 'Reports', hover: 'hover:border-amber-400/60 hover:bg-amber-400/15 hover:text-amber-100' },
    { path: marketplaceUrl, icon: Store, label: 'Marketplace', reload: true, hover: 'hover:border-orange-400/60 hover:bg-orange-400/15 hover:text-orange-100' },
    { path: '/web-weave', icon: BrainCircuit, label: 'Site Update', hover: 'hover:border-fuchsia-400/60 hover:bg-fuchsia-400/15 hover:text-fuchsia-100' },
    { path: '/now/desktop-orb', icon: Monitor, label: 'Desktop ORB Now', reload: true, hover: 'hover:border-indigo-400/60 hover:bg-indigo-400/15 hover:text-indigo-100' },
    { path: '/diagnostics', icon: Activity, label: 'Diagnostics', reload: true, hover: 'hover:border-rose-400/60 hover:bg-rose-400/15 hover:text-rose-100' },
    { path: '/cart', icon: ShoppingCart, label: 'Cart', hover: 'hover:border-yellow-400/60 hover:bg-yellow-400/15 hover:text-yellow-100' },
    ...(customer.is_admin ? [
      { path: '/admin/customers', icon: Shield, label: 'Admin', hover: 'hover:border-red-400/60 hover:bg-red-400/15 hover:text-red-100' },
      { path: 'http://localhost:21010/', icon: BrainCircuit, label: 'CALI CRM', reload: true, hover: 'hover:border-teal-400/60 hover:bg-teal-400/15 hover:text-teal-100' },
      { path: 'http://localhost:19000', icon: Mail, label: 'Prime Mail', reload: true, hover: 'hover:border-lime-400/60 hover:bg-lime-400/15 hover:text-lime-100' },
    ] : []),
    { path: '/account', icon: User, label: 'Account', hover: 'hover:border-slate-300/70 hover:bg-white/10 hover:text-white' },
  ];
  const pageTitle = location.pathname === '/welcome'
    ? 'Workspace Setup'
    : location.pathname.endsWith('/dock')
      ? 'Dock Station'
      : location.pathname.startsWith('/orbs/')
        ? 'Website ORBS'
        : navItems.find(n => location.pathname === n.path ||
          (n.path !== '/' && location.pathname.startsWith(n.path)))?.label || 'Dashboard';

  useEffect(() => {
    setIsSidebarOpen(false);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {isSidebarOpen && (
        <button
          type="button"
          className="fixed inset-0 z-20 bg-black/35 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
          aria-label="Close navigation menu"
        />
      )}

      <button
        type="button"
        className={`fixed left-0 top-24 z-40 flex h-12 w-10 items-center justify-center rounded-r-full bg-brand-dark text-white shadow-lg transition-transform md:hidden ${
          isSidebarOpen ? 'translate-x-60' : 'translate-x-0'
        }`}
        onClick={() => setIsSidebarOpen((open) => !open)}
        aria-label={isSidebarOpen ? 'Collapse navigation menu' : 'Open navigation menu'}
        aria-expanded={isSidebarOpen}
      >
        {isSidebarOpen ? <ChevronLeft className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      <aside
        className={`fixed left-0 top-0 z-30 flex h-full w-60 flex-col bg-brand-dark text-white shadow-xl transition-transform duration-200 md:translate-x-0 ${
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex-shrink-0 px-5 pb-2 pt-4">
          <div className="flex flex-col items-center gap-3 md:items-start">
            <img
              src={squareLogo}
              alt="Orb Weaver - Website ORB Intelligence Engine logo"
              className="h-20 w-full object-contain md:h-24"
            />
            <div>
              <h1 className="text-xl font-bold leading-tight">Orb Weaver</h1>
              <p className="mt-1 text-xs text-gray-400">Website ORB Intelligence Engine</p>
            </div>
          </div>
        </div>

        <nav className="mt-3 flex-1 overflow-y-auto px-3 pb-4">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path ||
                            (item.path !== '/' && location.pathname.startsWith(item.path));
            const navClassName = `mb-1.5 flex w-full items-center gap-2.5 rounded-full border px-3.5 py-2 text-left transition-all duration-200 ${
              isActive
                ? 'border-brand-orange bg-brand-orange text-brand-dark shadow-[0_8px_24px_rgba(249,115,22,0.24)]'
                : `border-white/10 bg-white/[0.035] text-gray-300 hover:-translate-y-0.5 hover:shadow-md ${item.hover}`
            }`;
            const contents = (
              <>
                <item.icon className="h-4 w-4 flex-shrink-0" />
                <span className="truncate text-[13px] font-bold">{item.label}</span>
              </>
            );
            return item.reload ? (
              <a key={item.path} href={item.path} className={navClassName} title={item.label} aria-label={item.label}>
                {contents}
              </a>
            ) : (
              <Link
                key={item.path}
                to={item.path}
                className={navClassName}
                title={item.label}
                aria-label={item.label}
              >
                {contents}
              </Link>
            );
          })}
        </nav>

        <div className="flex-shrink-0 p-4">
          <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-3">
            <p className="text-sm text-gray-300">Local Runtime</p>
            <p className="mt-1 text-xs text-gray-400">ORB intelligence workspace</p>
          </div>
        </div>
      </aside>

      <main className="min-h-screen flex-1 md:ml-60">
        <header className="sticky top-0 z-10 border-b border-gray-200 bg-white px-4 py-3 md:px-8">
          <div className="flex items-center justify-between gap-4">
            <h2 className="min-w-0 truncate text-xl font-bold text-gray-800 md:text-2xl">
              {pageTitle}
            </h2>
            <div className="flex min-w-0 items-center gap-3 md:gap-5">
              <Link to="/account" className="rounded-full p-2 hover:bg-gray-100" title="Account">
                <Settings className="h-5 w-5 text-gray-600" />
              </Link>
              <div className="hidden min-w-0 text-right sm:block">
                <p className="truncate text-sm font-semibold text-gray-900">{customer.business_name}</p>
                <p className="truncate text-xs text-gray-500">{customer.email}</p>
              </div>
              <img
                src={bannerLogo}
                alt="Orb Weaver - Website ORB Intelligence Engine"
                className="hidden h-20 w-56 object-contain lg:block xl:h-24 xl:w-72"
              />
            </div>
          </div>
        </header>

        <div className="p-4 md:p-8">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
