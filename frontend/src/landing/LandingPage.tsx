import React, { useState } from "react";
import PublicHeader from "../components/PublicHeader";
import { authStore } from "../services/api";
import { trackOnboardingEvent } from "../services/analytics";
import { createIntentGuestSession, LandingIntent } from "../onboarding/guestOnboarding";
import "./Landing.css";

const LandingPage: React.FC = () => {
  const [pendingTarget, setPendingTarget] = useState<string | null>(null);
  const [error, setError] = useState('');

  const begin = async (target: string, intent: LandingIntent, tier: 'basic' | 'enhanced' | 'premium' | null = null) => {
    if (intent === 'dashboard' && authStore.getToken()) {
      window.location.assign('/dashboard');
      return;
    }
    setError('');
    setPendingTarget(target);
    trackOnboardingEvent('landing_signup_cta_clicked', { intent, ...(tier ? { tier } : {}) });
    try {
      await createIntentGuestSession(target, intent, tier);
      window.location.assign(target);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'We could not start onboarding. Please try again.');
      setPendingTarget(null);
    }
  };

  return (
    <main className="ow-v2-page">
      <div className="ow-v2-grid" />
      <div className="ow-v2-noise" />

      <PublicHeader theme="dark" />

      <section className="ow-v2-hero">
        <div className="ow-v2-copy">
          <p className="ow-v2-kicker">WEBSITE ORB INTELLIGENCE ENGINE</p>

          <h1>
            Your website should know
            <span> how to help.</span>
          </h1>

          <p className="ow-v2-sub">
            Orb Weaver scans your website, maps what matters, and creates an ORB
            presence that helps visitors find the right next move.
          </p>

          <div className="ow-v2-actions">
            <button
              id="landing-free-preflight"
              data-orb-target="run-free-preflight"
              className="ow-v2-primary"
              onClick={() => begin('/signup?intent=preflight', 'preflight')}
              disabled={Boolean(pendingTarget)}
            >
              {pendingTarget === '/signup?intent=preflight' ? 'Preparing…' : 'Run a Free Preflight Scan'}
            </button>

            <button
              id="landing-dashboard"
              data-orb-target="launch-dashboard"
              className="ow-v2-secondary"
              onClick={() => begin('/login?next=/dashboard', 'dashboard')}
              disabled={Boolean(pendingTarget)}
            >
              Launch Dashboard
            </button>

            <a className="ow-v2-secondary" href="https://campaign.orbweaver.spruked.com">
              Campaign, Beta & Investor Portal
            </a>

            <a className="ow-v2-secondary" href="#how">
              See the Intelligence Layer
            </a>
          </div>

          {error && <p className="ow-v2-cta-error" role="alert">{error}</p>}

          <div className="ow-v2-proof">
            <span>NO REBUILD REQUIRED</span>
            <span>LOCAL-FIRST INTELLIGENCE</span>
            <span>YOUR DATA STAYS YOURS</span>
          </div>
        </div>
      </section>

      <section id="how" className="ow-v2-lower">
        <article>
          <span>01</span>
          <h2>Scan the site.</h2>
          <p>Structure, content, links, forms, routes, and visitor pathways.</p>
        </article>

        <article id="intelligence">
          <span>02</span>
          <h2>Build intelligence.</h2>
          <p>Semantic context, target maps, reports, and usable guidance.</p>
        </article>

        <article>
          <span>03</span>
          <h2>Give it presence.</h2>
          <p>A site-native ORB that knows where help is actually needed.</p>
        </article>
      </section>

      <section className="ow-v2-packages" aria-labelledby="package-heading">
        <div className="ow-v2-package-heading">
          <p className="ow-v2-kicker">WEBSITE ORBS</p>
          <h2 id="package-heading">Start with interest. Confirm fit with evidence.</h2>
          <p>Package eligibility and final recommendations follow Preflight, Crawl, and Final Audit.</p>
        </div>
        <div className="ow-v2-package-grid">
          {([
            ['basic', 'Basic', 'Visitor guidance for a focused public website.'],
            ['enhanced', 'Enhanced', 'Deeper routing across services and departments.'],
            ['premium', 'Premium', 'Branded guidance with broader semantic support.'],
          ] as const).map(([tier, label, description]) => (
            <article key={tier}>
              <span>{label}</span>
              <p>{description}</p>
              <button
                id={`landing-package-${tier}`}
                data-orb-target={`package-${tier}`}
                onClick={() => begin(`/signup?intent=package&tier=${tier}`, 'package', tier)}
                disabled={Boolean(pendingTarget)}
              >
                Explore {label}
              </button>
            </article>
          ))}
          <article>
            <span>Enterprise</span>
            <p>Preserve enterprise interest for an evidence-led supported discussion.</p>
            <button
              id="landing-enterprise"
              data-orb-target="package-enterprise"
              onClick={() => begin('/signup?intent=enterprise', 'enterprise')}
              disabled={Boolean(pendingTarget)}
            >
              Discuss Enterprise
            </button>
          </article>
        </div>
      </section>
    </main>
  );
};

export default LandingPage;
