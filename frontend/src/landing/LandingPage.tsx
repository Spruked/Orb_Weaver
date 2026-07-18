import React from "react";
import PublicHeader from "../components/PublicHeader";
import "./Landing.css";

const LandingPage: React.FC = () => {
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
            <a className="ow-v2-primary" href="/preflight">
              Run Free Preflight Scan
            </a>

            <a className="ow-v2-secondary" href="https://campaign.orbweaver.spruked.com">
              Campaign, Beta & Investor Portal
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
