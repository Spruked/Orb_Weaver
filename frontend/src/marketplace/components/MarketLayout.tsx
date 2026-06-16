import React from 'react';
import { Link } from 'react-router-dom';
import MarketNav from './MarketNav';
import '../styles/market-theme.css';

type MarketLayoutProps = {
  title: string;
  subtitle: string;
  children: React.ReactNode;
};

const MarketLayout: React.FC<MarketLayoutProps> = ({ title, subtitle, children }) => {
  return (
    <div className="ow-market-shell">
      <header className="ow-market-topbar">
        <div className="ow-market-topbar-inner">
          <Link to="/" className="ow-market-back-link">Back to Orb Weaver</Link>
        </div>
      </header>
      <main className="ow-market-main">
        <header className="ow-market-hero">
          <div>
            <p className="ow-market-kicker">ORB Marketplace Library</p>
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
          <aside className="ow-market-featured-offer" aria-label="Featured offer">
            <p>Featured Offer</p>
            <h2>Basic Visitor ORB</h2>
            <span>One-time website ORB install powered by Orb Weaver scan intelligence. No monthly SaaS fee.</span>
            <Link to="/marketplace/products/basic-visitor-orb" className="ow-market-featured-cta">
              View Product Page
            </Link>
          </aside>
        </header>

        <MarketNav />
        {children}
      </main>
      <footer className="ow-market-footer">ORB Marketplace Library</footer>
    </div>
  );
};

export default MarketLayout;
