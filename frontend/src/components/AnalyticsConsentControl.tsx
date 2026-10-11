import React, { useEffect, useState } from 'react';
import { AnalyticsConsent, getAnalyticsConsent, setAnalyticsConsent } from '../services/analytics';

const AnalyticsConsentControl: React.FC = () => {
  const [consent, setConsent] = useState<AnalyticsConsent>(getAnalyticsConsent);
  const [open, setOpen] = useState(consent === 'unknown');

  useEffect(() => {
    const handleConsentChange = () => setConsent(getAnalyticsConsent());
    window.addEventListener('orbweaver-analytics-consent-change', handleConsentChange);
    return () => window.removeEventListener('orbweaver-analytics-consent-change', handleConsentChange);
  }, []);

  const choose = (value: 'granted' | 'denied') => {
    setAnalyticsConsent(value);
    setConsent(value);
    setOpen(false);
  };

  return (
    <div style={{ position: 'fixed', bottom: 16, left: 16, zIndex: 1000, maxWidth: 360, color: '#e2e8f0' }}>
      {open ? (
        <section role="dialog" aria-label="Analytics privacy choices" style={{ border: '1px solid rgba(108, 215, 238, 0.35)', borderRadius: 12, background: 'rgba(3, 8, 16, 0.96)', padding: 16, boxShadow: '0 12px 30px rgba(0,0,0,.3)' }}>
          <p style={{ margin: '0 0 8px', fontWeight: 700 }}>Privacy choices</p>
          <p style={{ margin: '0 0 14px', fontSize: 13, lineHeight: 1.5, color: '#b8cad4' }}>
            Allow analytics on eligible public pages to help improve Orb Weaver. Analytics is off until you choose.
          </p>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" onClick={() => choose('granted')} style={{ border: 0, borderRadius: 8, background: '#6cd7ee', color: '#061A33', padding: '8px 12px', fontWeight: 700 }}>Allow analytics</button>
            <button type="button" onClick={() => choose('denied')} style={{ border: '1px solid rgba(255,255,255,.25)', borderRadius: 8, background: 'transparent', color: '#e2e8f0', padding: '8px 12px', fontWeight: 700 }}>Decline</button>
          </div>
        </section>
      ) : (
        <button type="button" onClick={() => setOpen(true)} style={{ border: '1px solid rgba(108, 215, 238, 0.35)', borderRadius: 999, background: 'rgba(3, 8, 16, 0.9)', color: '#b8cad4', padding: '7px 11px', fontSize: 12 }}>
          {consent === 'granted' ? 'Change privacy choices' : 'Privacy choices'}
        </button>
      )}
    </div>
  );
};

export default AnalyticsConsentControl;
