import React from 'react';
import { Link } from 'react-router-dom';
import { marketCollections } from '../data/marketplaceData';

const MarketCollectionRail: React.FC = () => {
  return (
    <section className="ow-market-collections" aria-label="Collections">
      {marketCollections.map((collection) => (
        <Link key={collection.id} to={`/marketplace/collection/${collection.id}`} className="ow-market-collection-card">
          <small className="ow-market-shelf-label">Shelf</small>
          <p>{collection.title}</p>
          <span>{collection.description}</span>
          <small>{collection.tags.join(' / ')}</small>
        </Link>
      ))}
    </section>
  );
};

export default MarketCollectionRail;
