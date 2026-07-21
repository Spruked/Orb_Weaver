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
  Sparkles,
  Activity,
  BrainCircuit,
  ChevronLeft,
  Menu
} from 'lucide-react';
import { Customer } from '../services/api';

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
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/projects', icon: Globe, label: 'Projects' },
    { path: '/crawl', icon: Search, label: 'Crawl Jobs' },
    { path: '/ga4', icon: BarChart3, label: 'GA4 Analytics' },
    { path: '/reports', icon: FileText, label: 'Reports' },
    { path: '/marketplace', icon: Store, label: 'Marketplace', reload: true },
    { path: '/web-weave', icon: BrainCircuit, label: 'Web Weave' },
    { path: '/demo', icon: Sparkles, label: 'Demo' },
    { path: '/diagnostics', icon: Activity, label: 'Diagnostics', reload: true },
    { path: '/cart', icon: ShoppingCart, label: 'Cart' },
    ...(customer.is_admin ? [{ path: '/admin/customers', icon: Shield, label: 'Admin' }] : []),
    { path: '/account', icon: User, label: 'Account' },
  ];
  const pageTitle = location.pathname === '/welcome'
    ? 'Workspace Setup'
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
        className={`fixed left-0 top-24 z-40 flex h-12 w-10 items-center justify-center rounded-r-lg bg-brand-dark text-white shadow-lg transition-transform md:hidden ${
          isSidebarOpen ? 'translate-x-64' : 'translate-x-0'
        }`}
        onClick={() => setIsSidebarOpen((open) => !open)}
        aria-label={isSidebarOpen ? 'Collapse navigation menu' : 'Open navigation menu'}
        aria-expanded={isSidebarOpen}
      >
        {isSidebarOpen ? <ChevronLeft className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      <aside
        className={`fixed left-0 top-0 z-30 flex h-full w-64 flex-col bg-brand-dark text-white shadow-xl transition-transform duration-200 md:w-64 md:translate-x-0 ${
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="px-2 pt-4 pb-2 flex-shrink-0 md:px-5">
          <div className="flex flex-col items-center gap-3 md:items-start">
            <img
              src={squareLogo}
              alt="Orb Weaver logo"
              className="h-20 w-full object-contain md:h-24 md:w-full"
            />
            <div>
              <h1 className="text-xl font-bold leading-tight">Orb Weaver</h1>
              <p className="text-xs text-gray-400 mt-1">Website ORB Intelligence Engine</p>
            </div>
          </div>
        </div>

        <nav className="mt-3 flex-1 overflow-y-auto px-2 pb-4 md:px-4">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path ||
                            (item.path !== '/' && location.pathname.startsWith(item.path));
            const navClassName = `mb-1.5 flex items-center justify-start gap-3 rounded-lg px-3 py-2.5 transition-all ${
              isActive
                ? 'bg-brand-orange text-white shadow-lg'
                : 'text-gray-300 hover:bg-white/10 hover:text-white'
            }`;
            const contents = (
              <>
                <item.icon className="w-4 h-4 flex-shrink-0" />
                <span className="text-sm font-medium">{item.label}</span>
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

        <div className="p-4 flex-shrink-0">
          <div className="bg-white/10 rounded-lg p-3">
            <p className="text-sm text-gray-300">Local Runtime</p>
            <p className="text-xs text-gray-400 mt-1">ORB intelligence workspace</p>
          </div>
        </div>
      </aside>

      <main className="min-h-screen flex-1 md:ml-64">
        <header className="sticky top-0 z-10 border-b border-gray-200 bg-white px-4 py-3 md:px-8">
          <div className="flex items-center justify-between gap-4">
            <h2 className="min-w-0 truncate text-xl font-bold text-gray-800 md:text-2xl">
              {pageTitle}
            </h2>
            <div className="flex min-w-0 items-center gap-3 md:gap-5">
              <Link to="/account" className="p-2 hover:bg-gray-100 rounded-lg" title="Account">
                <Settings className="w-5 h-5 text-gray-600" />
              </Link>
              <div className="hidden min-w-0 text-right sm:block">
                <p className="truncate text-sm font-semibold text-gray-900">{customer.business_name}</p>
                <p className="truncate text-xs text-gray-500">{customer.email}</p>
              </div>
              <img
                src={bannerLogo}
                alt="Orb Weaver"
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
