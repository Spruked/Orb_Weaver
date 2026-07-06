import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Demo from './pages/Demo';
import DiagnosticsPlaceholder from './pages/DiagnosticsPlaceholder';
import WebWeave from './pages/WebWeave';
import Projects from './pages/Projects';
import CrawlJobs from './pages/CrawlJobs';
import CrawlJob from './pages/CrawlJob';
import AuditReport from './pages/AuditReport';
import GA4Dashboard from './pages/GA4Dashboard';
import ReportCompiler from './pages/ReportCompiler';
import AuthPage from './pages/AuthPage';
import Account from './pages/Account';
import Cart from './pages/Cart';
import AdminCustomers from './pages/AdminCustomers';
import LegalPage from './pages/LegalPage';
import RouteScrollReset from './components/RouteScrollReset';
import LandingPage from './landing/LandingPage';
import PublicPreflight from './pages/PublicPreflight';
import PublicStaticPage from './pages/PublicStaticPage';
import MarketplaceRoutes from './marketplace/MarketplaceRoutes';
import { api, authStore, Customer } from './services/api';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  useEffect(() => {
    const loadCustomer = async () => {
      if (!authStore.getToken()) {
        setIsCheckingAuth(false);
        return;
      }
      try {
        setCustomer(await api.me());
      } catch {
        authStore.clearToken();
      } finally {
        setIsCheckingAuth(false);
      }
    };

    loadCustomer();
  }, []);

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {
      // Local token removal is authoritative for this client session.
    }
    authStore.clearToken();
    setCustomer(null);
  };

  const handleAuthenticated = (nextCustomer: Customer) => {
    const returnPath = window.location.pathname;
    setCustomer(nextCustomer);
    window.history.replaceState(
      null,
      '',
      returnPath === '/demo' || returnPath === '/diagnostics' ? returnPath : '/dashboard'
    );
  };

  if (isCheckingAuth) {
    return <div className="min-h-screen bg-gray-50 flex items-center justify-center text-gray-500">Loading account...</div>;
  }

  const publicPath = window.location.pathname;

  const renderPublicPage = (element: React.ReactNode) => (
    <QueryClientProvider client={queryClient}>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <RouteScrollReset />
        {element}
      </Router>
    </QueryClientProvider>
  );

  if (!customer && publicPath === '/') {
    return (
      <QueryClientProvider client={queryClient}>
        <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <RouteScrollReset />
          <LandingPage />
        </Router>
      </QueryClientProvider>
    );
  }

  if (!customer && publicPath === '/privacy') {
    return renderPublicPage(<LegalPage type="privacy" />);
  }
  if (!customer && publicPath === '/terms') {
    return renderPublicPage(<LegalPage type="terms" />);
  }
  if (publicPath === '/preflight') {
    return renderPublicPage(<PublicPreflight />);
  }
  if (publicPath === '/circus') {
    return renderPublicPage(<PublicStaticPage title="Orb Weaver Circus" src="/circus-page.html" />);
  }
  if (publicPath === '/marketplace' || publicPath.startsWith('/marketplace/')) {
    return renderPublicPage(<MarketplaceRoutes />);
  }
  if (!customer && publicPath === '/diagnostics') {
    return renderPublicPage(<AuthPage onAuthenticated={handleAuthenticated} />);
  }
  if (!customer && publicPath === '/demo') {
    return renderPublicPage(<AuthPage onAuthenticated={handleAuthenticated} />);
  }
  if (!customer && publicPath === '/login') {
    return renderPublicPage(<AuthPage onAuthenticated={handleAuthenticated} />);
  }

  if (!customer) {
    return renderPublicPage(<AuthPage onAuthenticated={handleAuthenticated} />);
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <RouteScrollReset />
        <Layout customer={customer}>
          <Routes>
            <Route path="/" element={<Dashboard customer={customer} />} />
            <Route path="/dashboard" element={<Dashboard customer={customer} />} />
            <Route path="/demo" element={<Demo customer={customer} />} />
            <Route path="/diagnostics" element={<DiagnosticsPlaceholder customer={customer} />} />
            <Route path="/web-weave" element={<WebWeave />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/crawl" element={<CrawlJobs />} />
            <Route path="/crawl/:jobId" element={<CrawlJob />} />
            <Route path="/audit/:auditId" element={<AuditReport />} />
            <Route path="/ga4/:propertyId" element={<GA4Dashboard />} />
            <Route path="/reports" element={<ReportCompiler />} />
            <Route path="/reports/:projectId" element={<ReportCompiler />} />
            <Route path="/cart" element={<Cart />} />
            <Route path="/admin/customers" element={<AdminCustomers />} />
            <Route path="/privacy" element={<LegalPage type="privacy" />} />
            <Route path="/terms" element={<LegalPage type="terms" />} />
            <Route path="/account" element={<Account customer={customer} onLogout={handleLogout} />} />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
