import React from 'react';
import { Link, useParams } from 'react-router-dom';
import MarketLayout from '../components/MarketLayout';
import MarketIndexCode from '../components/MarketIndexCode';
import { useMarketplace } from '../hooks/useMarketplace';

const MarketplaceProduct: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { items, addToCart } = useMarketplace();

  const item = items.find((entry) => entry.item_id === id);

  return (
    <MarketLayout
      title={item ? item.name : 'Product not found'}
      subtitle="Detailed listing card for standalone-ready marketplace routes."
    >
      {!item ? (
        <div className="ow-market-empty">
          Product record was not found. <Link to="/marketplace">Return to marketplace</Link>.
        </div>
      ) : (
        <article className="ow-market-product-detail">
          <header>
            <p>{item.badge}</p>
            <span>{item.price}</span>
          </header>
          <MarketIndexCode value={item.market_index_code} />
          <p>{item.description}</p>
          <ul className="ow-market-feature-list">
            {item.features.map((feature) => (
              <li key={feature}>{feature}</li>
            ))}
          </ul>
          <div className="ow-market-meta">
            <span>{item.rights_status}</span>
            <span>{item.rarity}</span>
            <span>{item.category}</span>
          </div>
          <div className="ow-market-actions">
            <button type="button" disabled={!item.purchasable} onClick={() => addToCart(item)}>
              {item.purchasable ? 'Add to Cart' : 'Planned'}
            </button>
            <Link to="/marketplace">Back to shelves</Link>
          </div>
        </article>
      )}
    </MarketLayout>
  );
};

export default MarketplaceProduct;
