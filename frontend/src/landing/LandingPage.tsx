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
            Orb Weaver scans and understands your website, finds technical and
            content problems, maps important controls, and creates an ORB that
            helps visitors find the right next action.
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

            <a className="ow-v2-secondary" href="#orb-tools">
              Explore ORB Tools
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

      <section className="ow-v2-intelligence" aria-labelledby="intelligence-heading">
        <div className="ow-v2-intelligence-copy">
          <p className="ow-v2-kicker">WEBSITE INTELLIGENCE</p>
          <h2 id="intelligence-heading">Understand your website before adding the ORB.</h2>
          <p>
            Orb Weaver examines site structure, technical SEO, content, links,
            forms, routes, analytics, and visitor pathways. It compiles that
            evidence into a Site World that gives Weaver verified knowledge of
            the website it serves.
          </p>
        </div>
      </section>

      <section id="orb-tools" className="ow-v2-tools" aria-labelledby="tools-heading">
        <div className="ow-v2-tools-heading">
          <p className="ow-v2-kicker">ORB SITE TOOLS</p>
          <h2 id="tools-heading">Explore the Orb Weaver website intelligence tools.</h2>
          <p>Use a tool directly, or ask Weaver to guide you.</p>
        </div>
        <ul className="ow-v2-tool-list">
          {[
            ['Website Preflight', 'A fast first review of technical, content, and search-visibility concerns.'],
            ['Site Crawl', 'Maps public pages, links, forms, routes, headings, metadata, and visitor pathways.'],
            ['Technical SEO Audit', 'Checks titles, descriptions, headings, canonicals, indexability, structured data, and other search signals.'],
            ['Final Audit', 'Verifies the completed website and produces evidence-based findings before an ORB package is recommended.'],
            ['Site World', 'Compiles the pages, controls, services, content, and verified facts Weaver needs to understand the website.'],
            ['Pointer Map', 'Connects Weaver to buttons, forms, links, products, and page sections so it can guide visitors accurately.'],
            ['Reports', 'Turns crawl and audit evidence into clear findings, priorities, and client-ready recommendations.'],
            ['ORB Visitor Guidance', 'Adds website-aware conversation, movement, pointing, navigation, and visitor assistance.'],
            ['Google Analytics', 'Connects GA4 behavior and visitor evidence to site findings and visitor pathways.'],
            ['Dashboard', 'Manages scans, audits, reports, Site World data, and ORB controls.'],
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
          <h2>Not sure where to begin?</h2>
          <p>Ask Weaver. He can explain each tool and guide you to the right next step.</p>
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
            <button
              id="landing-preflight-close"
              className="ow-v2-primary"
              onClick={() => window.location.assign('/preflight')}
              disabled={Boolean(pendingTarget)}
            >
              {pendingTarget === '/signup?intent=preflight' ? 'Preparing…' : 'Run a Free Preflight'}
            </button>
          </div>
        </div>
      </section>

      <section className="ow-v2-preflight-close" aria-labelledby="preflight-heading">
        <p className="ow-v2-kicker">START WITH PREFLIGHT</p>
        <h2 id="preflight-heading">Begin with a free website Preflight.</h2>
        <p>
          Every website is different. Preflight identifies the strongest next
          step before a package is recommended.
        </p>
        <button
          id="landing-start-preflight"
          className="ow-v2-primary"
          onClick={() => window.location.assign('/preflight')}
          disabled={Boolean(pendingTarget)}
        >
          {pendingTarget === '/signup?intent=preflight' ? 'Preparing…' : 'Start With Preflight'}
        </button>
      </section>
    </main>
  );
};

export default LandingPage;
