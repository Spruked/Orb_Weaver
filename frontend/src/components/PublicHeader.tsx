import React from 'react';
import { Link } from 'react-router-dom';
import './PublicCampaign.css';

type PublicHeaderProps = {
  theme?: 'dark' | 'light';
};

type PublicNavItem = {
  href: string;
  label: string;
  cta?: boolean;
  external?: boolean;
};

const publicNavItems: PublicNavItem[] = [
  { href: '/', label: 'Website ORB' },
  { href: '/how-it-works', label: 'How It Works' },
  { href: '/use-cases', label: 'Use Cases' },
  { href: '/founding-beta', label: 'Founding Beta' },
  { href: '/investor-contact', label: 'Investors' },
  { href: '/security', label: 'Vision & Product Philosophy' },
  { href: 'https://campaign.orbweaver.spruked.com', label: 'Campaign', external: true },
  { href: 'https://campaign.orbweaver.spruked.com/roi-calculator', label: 'Planning Calculator', cta: true, external: true },
];

const PublicHeader: React.FC<PublicHeaderProps> = ({ theme = 'dark' }) => {
  return (
    <header className={`ow-public-header ow-public-header-${theme}`}>
      <Link className="ow-public-brand" to="/" aria-label="Orb Weaver home" data-orb-target="orb-weaver-suite-logo">
        <img className="ow-public-brand-logo" src="/apple-touch-icon.png" alt="" aria-hidden="true" />
        <span>ORB WEAVER</span>
      </Link>
      <nav className="ow-public-nav" aria-label="Public site navigation">
        {publicNavItems.map((item) => (
          item.external ? (
            <a className={item.cta ? 'ow-public-nav-cta' : undefined} key={item.href} href={item.href}>
              {item.label}{item.cta && <span aria-hidden="true">→</span>}
            </a>
          ) : (
            <Link className={item.cta ? 'ow-public-nav-cta' : undefined} key={item.href} to={item.href}>
              {item.label}{item.cta && <span aria-hidden="true">→</span>}
            </Link>
          )
        ))}
      </nav>
    </header>
  );
};

export default PublicHeader;
