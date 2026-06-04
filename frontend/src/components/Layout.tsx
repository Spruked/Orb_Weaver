import React, { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Globe, 
  Search, 
  BarChart3, 
  Settings,
  FileText,
  User
} from 'lucide-react';
import { Customer } from '../services/api';

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
    { path: '/account', icon: User, label: 'Account' },
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-brand-dark text-white fixed h-full shadow-xl">
        <div className="p-6">
          <div className="flex items-center gap-3">
            <img
              src="/logositecrawler1600.png"
              alt="Orb Impact logo"
              className="w-10 h-10 rounded-md object-contain bg-white p-1"
            />
            <div>
              <h1 className="text-xl font-bold">Orb Weaver</h1>
              <p className="text-xs text-gray-400">Website ORB Intelligence Engine</p>
            </div>
          </div>
        </div>

        <nav className="mt-8 px-4">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || 
                            (item.path !== '/' && location.pathname.startsWith(item.path));
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-all ${
                  isActive 
                    ? 'bg-brand-orange text-white shadow-lg'
                    : 'text-gray-300 hover:bg-white/10 hover:text-white'
                }`}
              >
                <item.icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-6">
          <div className="bg-white/10 rounded-lg p-4">
            <p className="text-sm text-gray-300">Local Runtime</p>
            <p className="text-xs text-gray-400 mt-1">ORB intelligence workspace</p>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="ml-64 flex-1 min-h-screen">
        <header className="bg-white border-b border-gray-200 px-8 py-4 sticky top-0 z-10">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-gray-800">
              {navItems.find(n => location.pathname === n.path || 
                (n.path !== '/' && location.pathname.startsWith(n.path)))?.label || 'Dashboard'}
            </h2>
            <div className="flex items-center gap-4">
              <Link to="/account" className="p-2 hover:bg-gray-100 rounded-lg" title="Account">
                <Settings className="w-5 h-5 text-gray-600" />
              </Link>
              <div className="text-right">
                <p className="text-sm font-semibold text-gray-900">{customer.business_name}</p>
                <p className="text-xs text-gray-500">{customer.email}</p>
              </div>
              <div className="w-10 h-10 rounded-full border border-gray-200 bg-white flex items-center justify-center overflow-hidden">
                <img
                  src="/logositecrawler1600.png"
                  alt="Orb Impact"
                  className="w-8 h-8 object-contain"
                />
              </div>
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
