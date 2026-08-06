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
          <p className="ow-v2-kicker">EXECUTIVE WEBSITE PERFORMANCE</p>

          <h1>
            Turn website visits into
            <span> completed customer journeys.</span>
          </h1>

          <p className="ow-v2-sub">
            Orb Weaver helps visitors reach the right next step faster: less
            confusion, fewer abandoned forms and carts, clearer navigation,
            and stronger conversion outcomes across your website.
          </p>

          <div className="ow-v2-actions">
            <button
              id="landing-free-preflight"
              data-orb-target="run-free-preflight"
              className="ow-v2-primary"
              onClick={() => window.location.assign('/preflight')}
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

            <a className="ow-v2-secondary" href="/features">
              Explore Business Features
            </a>
          </div>

          {error && <p className="ow-v2-cta-error" role="alert">{error}</p>}

          <div className="ow-v2-proof">
            <span>REDUCE VISITOR FRICTION</span>
            <span>INCREASE COMPLETED JOURNEYS</span>
            <span>KEEP TRUST AND CONTROL</span>
          </div>
        </div>
      </section>

      <section className="ow-v2-intelligence" aria-labelledby="business-problem-heading">
        <div className="ow-v2-intelligence-copy">
          <p className="ow-v2-kicker">1. BUSINESS PROBLEM</p>
          <h2 id="business-problem-heading">Most websites make visitors work too hard.</h2>
          <p>
            Valuable visitors drop when pages feel unclear, navigation paths are
            fragmented, and next steps are easy to miss. Teams lose revenue when
            users abandon forms, leave carts, or never reach the right action.
          </p>
        </div>
      </section>

      <section className="ow-v2-intelligence" aria-labelledby="intelligence-heading">
        <div className="ow-v2-intelligence-copy">
          <p className="ow-v2-kicker">2. ORB WEAVER SOLUTION</p>
          <h2 id="intelligence-heading">Give your website an active guide that helps visitors finish.</h2>
          <p>
            Orb Weaver understands each page context, responds naturally to
            visitor intent, and guides people to verified next steps so they can
            complete high-value journeys with confidence.
          </p>
        </div>
      </section>

      <section id="orb-tools" className="ow-v2-tools" aria-labelledby="tools-heading">
        <div className="ow-v2-tools-heading">
          <p className="ow-v2-kicker">3. BUSINESS OUTCOMES</p>
          <h2 id="tools-heading">Move the metrics leadership teams care about.</h2>
          <p>Orb Weaver is designed to improve conversion quality, not just add a widget.</p>
        </div>
        <ul className="ow-v2-tool-list">
          {[
            ['Reduce visitor confusion', 'Help people understand where to go and what to do next.'],
            ['Increase completed journeys', 'Guide users from intent to completion across forms, checkout, and service workflows.'],
            ['Reduce abandonment', 'Support visitors at hesitation points before they drop out.'],
            ['Improve engagement quality', 'Create clearer, more useful interactions that keep visitors progressing.'],
            ['Strengthen trust', 'Use verified guidance and transparent behavior instead of guesswork.'],
            ['Accelerate decision speed', 'Shorten time from first visit to confident action.'],
          ].map(([title, description]) => (
            <li key={title} className="ow-v2-tool-item">
              <span className="ow-v2-tool-marker" aria-hidden="true" />
              <div className="ow-v2-tool-copy">
                <strong>{title}</strong>
                <span>{description}</span>
              </div>
            </li>
          ))}
        </ul>

        <div className="ow-v2-ask-weaver">
          <p className="ow-v2-kicker">4. INTERACTIVE GUIDANCE DEMONSTRATION</p>
          <h2>Watch Weaver guide visitors in real time.</h2>
          <p>
            See how interactive Point and Ping guidance helps visitors locate
            verified controls, follow clear actions, and complete their path.
          </p>
          <div className="ow-v2-actions ow-v2-actions-inline">
            <button
              id="landing-ask-weaver"
              data-orb-target="ask-weaver"
              className="ow-v2-secondary"
              onClick={() => window.dispatchEvent(new CustomEvent('orb:request-assistance', {
                detail: {
                  source: 'landing',
                  topic: 'orb-site-tools',
                },
              }))}
            >
              Ask Weaver
            </button>
            <a className="ow-v2-secondary" href="/how-it-works">
              See How It Works
            </a>
            <button
              id="landing-preflight-close"
              className="ow-v2-primary"
              onClick={() => window.location.assign('/preflight')}
              disabled={Boolean(pendingTarget)}
            >
              {pendingTarget === '/signup?intent=preflight' ? 'Preparing…' : 'Start Demonstration with Preflight'}
            </button>
          </div>
        </div>
      </section>

      <section className="ow-v2-intelligence" aria-labelledby="security-trust-heading">
        <div className="ow-v2-intelligence-copy">
          <p className="ow-v2-kicker">5. SECURITY AND TRUST</p>
          <h2 id="security-trust-heading">Trustworthy guidance, governed actions, accountable behavior.</h2>
          <p>
            Orb Weaver is designed to guide with verified state, bounded
            permissions, and explicit control governance so business guidance
            remains safe, truthful, and dependable.
          </p>
          <div className="ow-v2-actions ow-v2-actions-inline">
            <a className="ow-v2-secondary" href="/security">
              See Security Design
            </a>
          </div>
        </div>
      </section>

      <section className="ow-v2-intelligence" aria-labelledby="technology-overview-heading">
        <div className="ow-v2-intelligence-copy">
          <p className="ow-v2-kicker">6. TECHNOLOGY OVERVIEW</p>
          <h2 id="technology-overview-heading">Built on website intelligence, verification, and runtime orchestration.</h2>
          <p>
            Under the experience, Orb Weaver compiles website structure, verifies
            navigation targets, and coordinates guidance using governed runtime
            capabilities so visitor help remains precise and actionable.
          </p>
        </div>
      </section>

      <section className="ow-v2-preflight-close" aria-labelledby="preflight-heading">
        <p className="ow-v2-kicker">7. CALL TO ACTION</p>
        <h2 id="preflight-heading">Make your website easier to complete, not just easier to browse.</h2>
        <p>
          Start with a free Preflight to see where visitors lose momentum and
          where Orb Weaver can deliver measurable business impact.
        </p>
        <button
          id="landing-start-preflight"
          className="ow-v2-primary"
          onClick={() => window.location.assign('/preflight')}
          disabled={Boolean(pendingTarget)}
        >
          {pendingTarget === '/signup?intent=preflight' ? 'Preparing…' : 'Run Free Preflight'}
        </button>
      </section>
    </main>
  );
};

export default LandingPage;
