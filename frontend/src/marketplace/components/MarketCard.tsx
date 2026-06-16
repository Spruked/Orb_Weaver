import React from 'react';
import { Link } from 'react-router-dom';
import { MarketplaceItem } from '../../services/api';
import MarketIndexCode from './MarketIndexCode';

type MarketCardProps = {
  item: MarketplaceItem;
  onAddToCart: (item: MarketplaceItem) => void;
};

const MarketCard: React.FC<MarketCardProps> = ({ item, onAddToCart }) => {
  const primaryTier = item.tier_access?.[0] || 'basic';

  return (
    <article className="ow-market-card">
      <div className="ow-market-card-head">
        <p className="ow-market-chapter">{item.category}</p>
        <span className="ow-market-price-badge">{item.price}</span>
      </div>

      <div className="ow-market-orb-preview" aria-hidden="true" />
      <h3>{item.name}</h3>
      <MarketIndexCode value={item.market_index_code} />
      <p className="ow-market-card-description">{item.description}</p>

      <ul className="ow-market-feature-list">
        {item.features.slice(0, 3).map((feature) => (
          <li key={feature}>{feature}</li>
        ))}
      </ul>

      <div className="ow-market-meta">
        <span className="ow-market-tier-badge">Tier: {primaryTier}</span>
        <span>{item.badge}</span>
        <span>{item.rarity}</span>
      </div>

      <div className="ow-market-actions">
        <button
          type="button"
          disabled={!item.sku || !item.purchasable}
          onClick={() => onAddToCart(item)}
        >
          {item.purchasable ? 'Add to Cart' : 'Planned'}
        </button>
        <Link to={`/marketplace/product/${item.item_id}`}>Details</Link>
      </div>
    </article>
  );
};

export default MarketCard;
