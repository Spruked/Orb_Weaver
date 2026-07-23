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
import OrbsIntegration from './pages/OrbsIntegration';
import OrbDockStation from './pages/OrbDockStation';
import GA4Dashboard from './pages/GA4Dashboard';
import ReportCompiler from './pages/ReportCompiler';
import AuthPage, { AuthenticationOutcome } from './pages/AuthPage';
import WelcomeWorkspace from './pages/WelcomeWorkspace';
import Account from './pages/Account';
import Cart from './pages/Cart';
import AdminCustomers from './pages/AdminCustomers';
import LegalPage from './pages/LegalPage';
import RouteScrollReset from './components/RouteScrollReset';
import GoogleAnalyticsTracker from './components/GoogleAnalyticsTracker';
import LandingPage from './landing/LandingPage';
import PublicPreflight from './pages/PublicPreflight';
import PublicLeadPage from './pages/PublicLeadPage';
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
  const [authenticationOutcome, setAuthenticationOutcome] = useState<AuthenticationOutcome | null>(null);
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

  const handleAuthenticated = (nextCustomer: Customer, outcome?: AuthenticationOutcome) => {
    setCustomer(nextCustomer);
    setAuthenticationOutcome(outcome || null);
    const returnPath = window.location.pathname;
    const nextPath = outcome?.nextPath
      || (outcome?.mergeResult ? `/welcome?project=${encodeURIComponent(outcome.mergeResult.project_id)}` : null)
      || (outcome?.mergeError ? '/welcome?merge=pending' : null)
      || (returnPath === '/demo' || returnPath === '/diagnostics' ? returnPath : '/dashboard');
    window.history.replaceState(
      null,
      '',
      nextPath
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
        <GoogleAnalyticsTracker />
        {element}
      </Router>
    </QueryClientProvider>
  );

  if (!customer && publicPath === '/') {
    return (
      <QueryClientProvider client={queryClient}>
        <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <RouteScrollReset />
          <GoogleAnalyticsTracker />
          <LandingPage />
        </Router>
      </QueryClientProvider>
    );
  }

  if (publicPath === '/founding-beta') {
    return renderPublicPage(<PublicLeadPage type="beta" />);
  }
  if (publicPath === '/investor-contact') {
    return renderPublicPage(<PublicLeadPage type="investor" />);
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
  if (!customer && publicPath === '/signup') {
    return renderPublicPage(<AuthPage onAuthenticated={handleAuthenticated} initialMode="signup" />);
  }

  if (!customer) {
    return renderPublicPage(<AuthPage onAuthenticated={handleAuthenticated} />);
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <RouteScrollReset />
        <GoogleAnalyticsTracker />
        <Layout customer={customer}>
          <Routes>
            <Route path="/" element={<Dashboard customer={customer} />} />
            <Route path="/dashboard" element={<Dashboard customer={customer} />} />
            <Route path="/welcome" element={<WelcomeWorkspace customer={customer} initialMergeResult={authenticationOutcome?.mergeResult} initialMergeError={authenticationOutcome?.mergeError} />} />
            <Route path="/demo" element={<Demo customer={customer} />} />
            <Route path="/diagnostics" element={<DiagnosticsPlaceholder customer={customer} />} />
            <Route path="/web-weave" element={<WebWeave />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/crawl" element={<CrawlJobs />} />
            <Route path="/crawl/:jobId" element={<CrawlJob />} />
            <Route path="/audit/:auditId" element={<AuditReport />} />
            <Route path="/orbs/:projectId" element={<OrbsIntegration />} />
            <Route path="/orbs/:projectId/dock" element={<OrbDockStation />} />
            <Route path="/ga4" element={<GA4Dashboard />} />
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
