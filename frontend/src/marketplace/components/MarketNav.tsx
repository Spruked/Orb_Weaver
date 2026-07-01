import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const navItems = [
  { to: '/marketplace', label: 'Home' },
  { to: '/marketplace/collections', label: 'Collections' },
  { to: '/marketplace/search', label: 'Search' },
  { to: '/cart', label: 'Cart' },
];

const MarketNav: React.FC = () => {
  const location = useLocation();

  return (
    <nav className="ow-market-nav" aria-label="Marketplace navigation">
      {navItems.map((item) => {
        const isActive =
          item.to === '/marketplace'
            ? location.pathname === '/marketplace'
            : location.pathname.startsWith(item.to);

        return (
          <Link key={item.to} to={item.to} className={isActive ? 'active' : ''}>
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
};

export default MarketNav;
