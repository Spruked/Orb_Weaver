import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { MarketplaceItem } from '../../services/api';
import MarketIndexCode from './MarketIndexCode';

type MarketCardProps = {
  item: MarketplaceItem;
  onAddToCart: (item: MarketplaceItem) => void;
};

const AUTHORITY_PRODUCT_SLUGS: Record<string, string> = {
  orb_basic_visitor: 'basic-visitor-orb',
  orb_enhanced_website: 'enhanced-website-orb',
  orb_premium_website: 'premium-website-orb',
};

const MarketCard: React.FC<MarketCardProps> = ({ item, onAddToCart }) => {
  const navigate = useNavigate();
  const [imageFailed, setImageFailed] = React.useState(false);
  const primaryTier = item.tier_access?.[0] || 'basic';
  const authoritySlug = AUTHORITY_PRODUCT_SLUGS[item.item_id];
  const isAuthorityProduct = Boolean(authoritySlug);
  const productHref = authoritySlug ? `/marketplace/products/${authoritySlug}` : `/marketplace/product/${item.item_id}`;

  const imageSrc = React.useMemo(() => {
    if (!item.image_src) {
      return null;
    }
    const trimmed = item.image_src.trim();
    if (!trimmed) {
      return null;
    }
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://') || trimmed.startsWith('/')) {
      return trimmed;
    }
    return `/${trimmed}`;
  }, [item.image_src]);

  const openProduct = () => {
    navigate(productHref);
  };

  return (
    <article
      className="ow-market-card ow-market-card-clickable"
      role="link"
      tabIndex={0}
      aria-label={`Open ${item.name}`}
      onClick={openProduct}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          openProduct();
        }
      }}
    >
      <div className="ow-market-card-head">
        <p className="ow-market-chapter">{item.category}</p>
        <div className="ow-market-card-head-right">
          <span className="ow-market-price-badge">{item.price}</span>
          {isAuthorityProduct ? <span className="ow-market-authority-badge">Authority Product</span> : null}
        </div>
      </div>

      {imageSrc && !imageFailed ? (
        <img className="ow-market-orb-image" src={imageSrc} alt={item.name} loading="lazy" onError={() => setImageFailed(true)} />
      ) : (
        <div className="ow-market-orb-preview" aria-hidden="true" />
      )}
      <h3>{item.name}</h3>
      <MarketIndexCode value={item.market_index_code} />
      <p className="ow-market-card-description">{item.description}</p>

      <ul className="ow-market-feature-list">
        {item.features.slice(0, 2).map((feature) => (
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
          onClick={(event) => {
            event.stopPropagation();
            onAddToCart(item);
          }}
        >
          {item.purchasable ? 'Add to Cart' : 'Planned'}
        </button>
        <Link
          to={productHref}
          onClick={(event) => {
            event.stopPropagation();
          }}
        >
          View Product Page
        </Link>
      </div>
    </article>
  );
};

export default MarketCard;
