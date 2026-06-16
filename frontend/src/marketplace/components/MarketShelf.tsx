import React from 'react';
import { MarketplaceItem } from '../../services/api';
import MarketCard from './MarketCard';

type MarketShelfProps = {
  items: MarketplaceItem[];
  emptyCopy: string;
  onAddToCart: (item: MarketplaceItem) => void;
};

const MarketShelf: React.FC<MarketShelfProps> = ({ items, emptyCopy, onAddToCart }) => {
  if (!items.length) {
    return <div className="ow-market-empty">{emptyCopy}</div>;
  }

  return (
    <section className="ow-market-grid" aria-label="Marketplace results">
      {items.map((item) => (
        <MarketCard key={item.item_id} item={item} onAddToCart={onAddToCart} />
      ))}
    </section>
  );
};

export default MarketShelf;
