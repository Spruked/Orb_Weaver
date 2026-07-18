import React from 'react';

type PublicHeaderProps = {
  theme?: 'dark' | 'light';
};

const publicNavItems = [
  { href: '/', label: 'Home' },
  { href: '/preflight', label: 'Preflight' },
  { href: '/founding-beta', label: 'Founding Beta' },
  { href: '/investor-contact', label: 'Investors' },
  { href: '/marketplace', label: 'Marketplace' },
  { href: '/demo', label: 'Demonstration Station' },
  { href: '/login', label: 'Login' },
];

const PublicHeader: React.FC<PublicHeaderProps> = ({ theme = 'dark' }) => {
  return (
    <header className={`ow-public-header ow-public-header-${theme}`}>
      <a className="ow-public-brand" href="/" aria-label="Orb Weaver home">
        <span className="ow-public-brand-dot" />
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
