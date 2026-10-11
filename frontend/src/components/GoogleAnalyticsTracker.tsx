import { useEffect } from 'react';
import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { getAnalyticsConsent, trackPageView } from '../services/analytics';

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
    dataLayer?: unknown[][];
  }
}

const GoogleAnalyticsTracker: React.FC<{ enabled?: boolean }> = ({ enabled = true }) => {
  const { pathname } = useLocation();
  const [consent, setConsent] = useState(getAnalyticsConsent);

  useEffect(() => {
    const handleConsentChange = () => setConsent(getAnalyticsConsent());
    window.addEventListener('orbweaver-analytics-consent-change', handleConsentChange);
    return () => window.removeEventListener('orbweaver-analytics-consent-change', handleConsentChange);
  }, []);

  useEffect(() => {
    if (enabled && consent === 'granted') trackPageView(pathname, document.title);
  }, [consent, enabled, pathname]);

  return null;
};

export default GoogleAnalyticsTracker;
