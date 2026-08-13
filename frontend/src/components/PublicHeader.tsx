import React from 'react';

type PublicHeaderProps = {
  theme?: 'dark' | 'light';
};

const publicNavItems = [
  { href: '/', label: 'Home' },
  { href: '/features', label: 'Features' },
  { href: '/lidar-guidance', label: 'LiDAR Guidance' },
  { href: '/how-it-works', label: 'How It Works' },
  { href: '/security', label: 'Security' },
  { href: '/now/desktop-orb', label: 'Desktop ORB' },
  { href: 'https://campaign.orbweaver.spruked.com', label: 'Campaign' },
  { href: '/preflight', label: 'Preflight' },
  { href: '/founding-beta', label: 'Beta' },
  { href: '/investor-contact', label: 'Investors' },
  { href: '/marketplace', label: 'Marketplace' },
  { href: '/login', label: 'Login' },
];

const PublicHeader: React.FC<PublicHeaderProps> = ({ theme = 'dark' }) => {
  return (
    <header className={`ow-public-header ow-public-header-${theme}`}>
      <a className="ow-public-brand" href="/" aria-label="Orb Weaver home" data-orb-target="orb-weaver-suite-logo">
        <img className="ow-public-brand-logo" src="/apple-touch-icon.png" alt="" aria-hidden="true" />
        <span>ORB WEAVER</span>
      </a>
      <nav className="ow-public-nav" aria-label="Public site navigation">
        {publicNavItems.map((item) => (
          <a key={item.href} href={item.href}>
            {item.label}
          </a>
        ))}
      </nav>
    </header>
  );
};

export default PublicHeader;
