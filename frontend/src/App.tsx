import React, { useEffect, useState } from 'react';
import { Navigate, Routes, Route, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import DiagnosticsPlaceholder from './pages/DiagnosticsPlaceholder';
import DesktopOrbNow from './pages/DesktopOrbNow';
import WebWeave from './pages/WebWeave';
import Projects from './pages/Projects';
import ScanCenter from './pages/ScanCenter';
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
import PublicHowItWorks from './pages/PublicHowItWorks';
import PublicFeatures from './pages/PublicFeatures';
import PublicSecurity from './pages/PublicSecurity';
import LidarGuidance from './pages/LidarGuidance';
import { api, authStore, Customer } from './services/api';
import { marketplaceUrl } from './services/marketplaceUrl';
import './index.css';

const MarketplaceRedirect: React.FC = () => {
  const location = useLocation();

  useEffect(() => {
    const remainingPath = location.pathname.replace(/^\/marketplace/, '');
    window.location.replace(`${marketplaceUrl}/marketplace${remainingPath}${location.search}${location.hash}`);
  }, [location]);

  return <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-300">Opening ORB Marketplace…</div>;
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  const location = useLocation();
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
      || (returnPath === '/diagnostics' ? returnPath : '/dashboard');
    window.history.replaceState(null, '', nextPath);
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  if (isCheckingAuth) {
    return <div className="min-h-screen bg-gray-50 flex items-center justify-center text-gray-500">Loading account...</div>;
  }

  const publicPath = location.pathname;

  const renderPublicPage = (element: React.ReactNode) => (
    <QueryClientProvider client={queryClient}>
      <RouteScrollReset />
      <GoogleAnalyticsTracker />
      {element}
    </QueryClientProvider>
  );

  if (!customer && publicPath === '/') {
    return renderPublicPage(<LandingPage />);
  }

  if (publicPath === '/demo') {
    return renderPublicPage(<Navigate to="/" replace />);
  }
  if (publicPath === '/founding-beta') {
    return renderPublicPage(<PublicLeadPage type="beta" />);
  }
  if (publicPath === '/investor-contact') {
    return renderPublicPage(<PublicLeadPage type="investor" />);
  }
  if (publicPath === '/now/desktop-orb') {
    return renderPublicPage(<DesktopOrbNow />);
  }
  if (publicPath === '/features') {
    return renderPublicPage(<PublicFeatures />);
  }
  if (publicPath === '/lidar-guidance') {
    return renderPublicPage(<LidarGuidance />);
  }
  if (publicPath === '/how-it-works') {
    return renderPublicPage(<PublicHowItWorks />);
  }
  if (publicPath === '/security') {
    return renderPublicPage(<PublicSecurity />);
  }
  if (!customer && publicPath === '/privacy') {
    return renderPublicPage(<LegalPage type="privacy" />);
  }
  if (!customer && publicPath === '/terms') {
    return renderPublicPage(<LegalPage type="terms" />);
  }
  if (!customer && publicPath === '/weaving') {
    return renderPublicPage(<LegalPage type="weaving" />);
  }
  if (publicPath === '/preflight') {
    return renderPublicPage(<PublicPreflight />);
  }
  if (publicPath === '/marketplace' || publicPath.startsWith('/marketplace/')) {
    return renderPublicPage(<MarketplaceRedirect />);
  }
  if (!customer && publicPath === '/diagnostics') {
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
      <RouteScrollReset />
      <GoogleAnalyticsTracker />
      <Layout customer={customer}>
        <Routes>
          <Route path="/" element={<Dashboard customer={customer} />} />
          <Route path="/dashboard" element={<Dashboard customer={customer} />} />
          <Route path="/welcome" element={<WelcomeWorkspace customer={customer} initialMergeResult={authenticationOutcome?.mergeResult} initialMergeError={authenticationOutcome?.mergeError} />} />
          <Route path="/demo" element={<Navigate to="/" replace />} />
          <Route path="/diagnostics" element={<DiagnosticsPlaceholder customer={customer} />} />
          <Route path="/now/desktop-orb" element={<DesktopOrbNow />} />
          <Route path="/web-weave" element={<WebWeave />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/scan-center" element={<ScanCenter />} />
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
          <Route path="/checkout/success" element={<Cart />} />
          <Route path="/admin/customers" element={<AdminCustomers />} />
          <Route path="/privacy" element={<LegalPage type="privacy" />} />
          <Route path="/terms" element={<LegalPage type="terms" />} />
          <Route path="/account" element={<Account customer={customer} onLogout={handleLogout} />} />
        </Routes>
      </Layout>
    </QueryClientProvider>
  );
}

export default App;
