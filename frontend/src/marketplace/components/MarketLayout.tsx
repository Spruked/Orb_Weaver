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
          <span className="ow-market-topbar-note">Private catalog environment</span>
        </div>
      </header>
      <main className="ow-market-main">
        <header className="ow-market-hero">
          <div>
            <p className="ow-market-kicker">ORB Marketplace Library</p>
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
          <aside className="ow-market-doctrine">
            <p>Doctrine</p>
            <h2>ORB-MKT Index</h2>
            <span>Catalog-first product architecture for standalone growth.</span>
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
