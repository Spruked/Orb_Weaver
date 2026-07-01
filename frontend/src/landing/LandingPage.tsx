import React from "react";
import "./Landing.css";

const LandingPage: React.FC = () => {
  return (
    <main className="ow-v2-page">
      <div className="ow-v2-grid" />
      <div className="ow-v2-noise" />

      <header className="ow-v2-header">
        <div className="ow-v2-brand">
          <span className="ow-v2-brand-dot" />
          <span>ORB WEAVER</span>
        </div>

        <div className="ow-v2-orb-indicator" aria-label="ORB status">
          <span />
          <strong>ORB online</strong>
        </div>

        <nav className="ow-v2-nav">
          <a href="#how">How It Works</a>
          <a href="#intelligence">Intelligence</a>
          <a href="/marketplace">Marketplace</a>
          <a className="ow-v2-demo-required" href="/login">
            Demo: must be logged into an account to use
          </a>
          <a href="/login">Launch Dashboard</a>
        </nav>
      </header>

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
            <a className="ow-v2-primary" href="/preflight">
              Run Free Preflight Scan
            </a>

            <a className="ow-v2-secondary" href="#how">
              See the Intelligence Layer
            </a>
          </div>

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
    </main>
  );
};

export default LandingPage;
