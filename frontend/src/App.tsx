import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import CrawlJob from './pages/CrawlJob';
import AuditReport from './pages/AuditReport';
import GA4Dashboard from './pages/GA4Dashboard';
import ReportCompiler from './pages/ReportCompiler';
import AuthPage from './pages/AuthPage';
import Account from './pages/Account';
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

  if (isCheckingAuth) {
    return <div className="min-h-screen bg-gray-50 flex items-center justify-center text-gray-500">Loading account...</div>;
  }

  if (!customer) {
    return <AuthPage onAuthenticated={setCustomer} />;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout customer={customer}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/crawl/:jobId" element={<CrawlJob />} />
            <Route path="/audit/:auditId" element={<AuditReport />} />
            <Route path="/ga4/:propertyId" element={<GA4Dashboard />} />
            <Route path="/reports/:projectId" element={<ReportCompiler />} />
            <Route path="/account" element={<Account customer={customer} onLogout={handleLogout} />} />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
