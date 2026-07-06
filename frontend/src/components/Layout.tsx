import React, { ReactNode } from 'react';
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
  Tent,
  Activity,
  BrainCircuit
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

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/projects', icon: Globe, label: 'Projects' },
    { path: '/crawl', icon: Search, label: 'Crawl Jobs' },
    { path: '/ga4', icon: BarChart3, label: 'GA4 Analytics' },
    { path: '/reports', icon: FileText, label: 'Reports' },
    { path: '/marketplace', icon: Store, label: 'Marketplace', reload: true },
    { path: '/web-weave', icon: BrainCircuit, label: 'Web Weave' },
    { path: '/demo', icon: Sparkles, label: 'Demo' },
    { path: '/circus', icon: Tent, label: 'Circus', reload: true },
    { path: '/diagnostics', icon: Activity, label: 'Diagnostics', reload: true },
    { path: '/cart', icon: ShoppingCart, label: 'Cart' },
    ...(customer.is_admin ? [{ path: '/admin/customers', icon: Shield, label: 'Admin' }] : []),
    { path: '/account', icon: User, label: 'Account' },
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-brand-dark text-white fixed h-full shadow-xl flex flex-col">
        <div className="px-5 pt-4 pb-2 flex-shrink-0">
          <div className="flex flex-col gap-3">
            <img
              src={squareLogo}
              alt="Orb Weaver logo"
              className="h-24 w-full object-contain"
            />
            <div>
              <h1 className="text-xl font-bold leading-tight">Orb Weaver</h1>
              <p className="text-xs text-gray-400 mt-1">Website ORB Intelligence Engine</p>
            </div>
          </div>
        </div>

        <nav className="mt-3 px-4 pb-4 flex-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || 
                            (item.path !== '/' && location.pathname.startsWith(item.path));
            const navClassName = `flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1.5 transition-all ${
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
              <a key={item.path} href={item.path} className={navClassName}>
                {contents}
              </a>
            ) : (
              <Link
                key={item.path}
                to={item.path}
                className={navClassName}
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

      {/* Main Content */}
      <main className="ml-64 flex-1 min-h-screen">
        <header className="bg-white border-b border-gray-200 px-8 py-3 sticky top-0 z-10">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-gray-800">
              {navItems.find(n => location.pathname === n.path || 
                (n.path !== '/' && location.pathname.startsWith(n.path)))?.label || 'Dashboard'}
            </h2>
            <div className="flex items-center gap-5">
              <Link to="/account" className="p-2 hover:bg-gray-100 rounded-lg" title="Account">
                <Settings className="w-5 h-5 text-gray-600" />
              </Link>
              <div className="text-right">
                <p className="text-sm font-semibold text-gray-900">{customer.business_name}</p>
                <p className="text-xs text-gray-500">{customer.email}</p>
              </div>
              <img
                src={bannerLogo}
                alt="Orb Weaver"
                className="hidden h-24 w-72 object-contain sm:block"
              />
            </div>
          </div>
        </header>

        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
