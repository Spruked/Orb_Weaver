import React, { useEffect, useMemo, useState } from 'react';
import PublicHeader from '../components/PublicHeader';
import {
  ApiError,
  api,
  authStore,
  Customer,
  OrbsGuestMergeResult,
} from '../services/api';
import { trackOnboardingEvent } from '../services/analytics';
import {
  clearMergedGuestReference,
  createIntentGuestSession,
  intentFromLocation,
  mergeIdempotencyKey,
} from '../onboarding/guestOnboarding';
import './Onboarding.css';

interface AuthenticationOutcome {
  mergeResult?: OrbsGuestMergeResult;
  mergeError?: string;
  nextPath?: string;
}

interface AuthPageProps {
  onAuthenticated: (customer: Customer, outcome?: AuthenticationOutcome) => void;
  initialMode?: 'login' | 'signup';
}

const AuthPage: React.FC<AuthPageProps> = ({ onAuthenticated, initialMode = 'login' }) => {
  const [mode, setMode] = useState<'login' | 'signup'>(initialMode);
  const [step, setStep] = useState<1 | 2>(1);
  const [legal, setLegal] = useState({ terms: false, privacy: false });
  const [form, setForm] = useState({
    full_name: '',
    business_name: '',
    email: '',
    password: '',
    website_url: '',
    website_confirmation: '',
  });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const intent = useMemo(() => intentFromLocation(), []);
  const isSignup = mode === 'signup';

  useEffect(() => {
    if (isSignup) trackOnboardingEvent('onboarding_started', { intent: intent.intent });
  }, [intent.intent, isSignup]);

  const update = (field: keyof typeof form, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const continueToWebsite = () => {
    setError('');
    if (!form.full_name.trim() || !form.business_name.trim() || !form.email.trim() || form.password.length < 8) {
      setError('Complete your name, business, email, and a password of at least eight characters.');
      return;
    }
    setStep(2);
    trackOnboardingEvent('onboarding_step_completed', { intent: intent.intent, step: 'account_details' });
  };

  const submitLogin = async () => {
    const response = await api.login({ email: form.email, password: form.password });
    authStore.setToken(response.token);
    const next = new URLSearchParams(window.location.search).get('next');
    onAuthenticated(response.customer, { nextPath: next?.startsWith('/') ? next : '/dashboard' });
  };

  const submitSignup = async () => {
    if (!form.website_url.trim() || form.website_url.trim() !== form.website_confirmation.trim()) {
      throw new Error('Enter the website twice so Weaver can confirm the correct project.');
    }
    if (!legal.terms || !legal.privacy) {
      throw new Error('Accept the Terms and Privacy Policy to create the account.');
    }

    const guest = await createIntentGuestSession(
      intent.originalDestination,
      intent.intent,
      intent.tier,
      form.website_url.trim(),
      'website_confirmed'
    );
    trackOnboardingEvent('onboarding_step_completed', { intent: intent.intent, step: 'website_confirmed' });

    const response = await api.signup({
      email: form.email.trim(),
      password: form.password,
      full_name: form.full_name.trim(),
      business_name: form.business_name.trim(),
      country: 'US',
      guest_session_id: guest.guest_session_id,
    });
    authStore.setToken(response.token);
    trackOnboardingEvent('account_created', { intent: intent.intent });

    try {
      const mergeResult = await api.mergeOrbsGuestSession(guest.guest_session_id, {
        schema: 'orb_weaver.orbs_guest_merge_request.v1',
        guest_session_id: guest.guest_session_id,
        idempotency_key: mergeIdempotencyKey(guest.guest_session_id),
        project_display_name: form.business_name.trim(),
      });
      clearMergedGuestReference(guest.guest_session_id);
      trackOnboardingEvent('guest_merge_completed', { intent: intent.intent, outcome: 'success' });
      trackOnboardingEvent('website_project_created', { intent: intent.intent });
      trackOnboardingEvent('onboarding_completed', { intent: intent.intent });
      onAuthenticated(response.customer, { mergeResult });
    } catch (mergeFailure) {
      const message =
        mergeFailure instanceof ApiError
          ? `${mergeFailure.message} Your account is safe; retry the project merge from Welcome.`
          : 'Your account is ready, but the project merge needs to be retried from Welcome.';
      onAuthenticated(response.customer, { mergeError: message });
    }
  };

  const submit = async () => {
    setError('');
    setIsSubmitting(true);
    try {
      if (isSignup) await submitSignup();
      else await submitLogin();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Authentication failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const guidance = !isSignup
    ? 'Sign in and I’ll resume from the latest authoritative workspace state.'
    : step === 1
      ? 'I’ll help you set up your workspace and add the website you want to review. This should only take about a minute.'
      : 'Confirm the website you want Orb Weaver to review. I will carry it and your original goal into the new project.';

  const activateWeaver = () => {
    const globalWeaver = document.querySelector<HTMLButtonElement>('.ow-v2-orb-body');
    globalWeaver?.click();
  };

  return (
    <div className="onboarding-shell">
      <PublicHeader theme="light" />
      <main className="onboarding-layout">
        <section className="onboarding-card" aria-labelledby="onboarding-title">
          <div className="onboarding-brand">
            <img src="/orbweaverlogo1024.png" alt="Orb Weaver" />
            <div>
              <p>GUIDED WORKSPACE SETUP</p>
              <h1 id="onboarding-title">{isSignup ? 'Create your Orb Weaver workspace' : 'Welcome back'}</h1>
            </div>
          </div>

          <div className="onboarding-mode-switch" aria-label="Authentication mode">
            <button type="button" onClick={() => setMode('login')} aria-pressed={!isSignup}>Login</button>
            <button type="button" onClick={() => setMode('signup')} aria-pressed={isSignup}>Create Account</button>
          </div>

          {isSignup && (
            <div className="onboarding-progress" aria-label={`Step ${step} of 2`}>
              <span className={step >= 1 ? 'active' : ''}>1. Account</span>
              <i />
              <span className={step >= 2 ? 'active' : ''}>2. Website</span>
            </div>
          )}

          {(!isSignup || step === 1) && (
            <div className="onboarding-fields">
              {isSignup && (
                <>
                  <label htmlFor="onboarding-full-name">Full name</label>
                  <input id="onboarding-full-name" data-orb-target="full-name-field" autoComplete="name" value={form.full_name} onChange={(event) => update('full_name', event.target.value)} />
                  <label htmlFor="onboarding-business-name">Business name</label>
                  <input id="onboarding-business-name" data-orb-target="business-name-field" autoComplete="organization" value={form.business_name} onChange={(event) => update('business_name', event.target.value)} />
                </>
              )}
              <label htmlFor="onboarding-email">Email</label>
              <input id="onboarding-email" data-orb-target="email-field" type="email" autoComplete="email" value={form.email} onChange={(event) => update('email', event.target.value)} />
              <label htmlFor="onboarding-password">Password</label>
              <div id="onboarding-password-container" data-orb-target="password-container">
                <input id="onboarding-password" type="password" autoComplete={isSignup ? 'new-password' : 'current-password'} value={form.password} onChange={(event) => update('password', event.target.value)} />
              </div>
            </div>
          )}

          {isSignup && step === 2 && (
            <div className="onboarding-fields">
              <label htmlFor="onboarding-website">Website URL</label>
              <input id="onboarding-website" data-orb-target="website-url-field" type="url" inputMode="url" placeholder="https://example.com" value={form.website_url} onChange={(event) => update('website_url', event.target.value)} />
              <label htmlFor="onboarding-website-confirmation">Confirm website</label>
              <input id="onboarding-website-confirmation" type="url" inputMode="url" placeholder="Enter the same website again" value={form.website_confirmation} onChange={(event) => update('website_confirmation', event.target.value)} />
              <div className="onboarding-legal">
                <label><input type="checkbox" checked={legal.terms} onChange={(event) => setLegal({ ...legal, terms: event.target.checked })} /> I agree to the <a href="/terms">Terms</a>.</label>
                <label><input type="checkbox" checked={legal.privacy} onChange={(event) => setLegal({ ...legal, privacy: event.target.checked })} /> I agree to the <a href="/privacy">Privacy Policy</a>.</label>
              </div>
            </div>
          )}

          {intent.intent === 'package' && isSignup && (
            <p className="onboarding-intent-note">Your {intent.tier || 'selected'} package interest is preserved. Eligibility and the final recommendation require Preflight, Crawl, and Final Audit.</p>
          )}
          {intent.intent === 'enterprise' && isSignup && (
            <p className="onboarding-intent-note">Your enterprise interest is preserved for an evidence-led supported integration discussion.</p>
          )}

          {error && <div className="onboarding-error" role="alert">{error}</div>}

          <div className="onboarding-actions">
            {isSignup && step === 2 && <button type="button" className="secondary" onClick={() => setStep(1)}>Back</button>}
            {isSignup && step === 1 ? (
              <button id="onboarding-continue" data-orb-target="continue" type="button" className="primary" onClick={continueToWebsite}>Continue</button>
            ) : (
              <button id={isSignup ? 'onboarding-create-account' : 'onboarding-login'} data-orb-target={isSignup ? 'create-account' : 'login'} type="button" className="primary" disabled={isSubmitting} onClick={submit}>
                {isSubmitting ? 'Working…' : isSignup ? 'Create Account' : 'Login'}
              </button>
            )}
          </div>
        </section>

        <aside className="weaver-guide" aria-live="polite">
          <button type="button" className="weaver-guide-orb" onClick={activateWeaver} aria-label="Activate Weaver voice guidance"><span /></button>
          <p className="weaver-guide-label">WEAVER · OPTIONAL GUIDANCE</p>
          <h2>{isSignup ? `Step ${step} of 2` : 'Resume your workspace'}</h2>
          <p>{guidance}</p>
          <p className="weaver-guide-footnote">Click Weaver whenever you want more help. Voice begins only when you activate it.</p>
        </aside>
      </main>
    </div>
  );
};

export type { AuthenticationOutcome };
export default AuthPage;
