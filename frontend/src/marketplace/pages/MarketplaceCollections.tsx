import React from 'react';
import { Link, useParams } from 'react-router-dom';
import MarketCollectionRail from '../components/MarketCollectionRail';
import MarketLayout from '../components/MarketLayout';
import MarketShelf from '../components/MarketShelf';
import { fallbackMarketplaceItems, marketCollections } from '../data/marketplaceData';
import { useMarketplace } from '../hooks/useMarketplace';

const collectionToCategories: Record<string, string[]> = {
  'website-orbs': ['orbs'],
  'dock-and-diagnostics': ['dock', 'diagnostics'],
  'skins-and-behaviors': ['skins', 'packs'],
  'scan-bundles': ['credits'],
};

const MarketplaceCollections: React.FC = () => {
  const { id } = useParams<{ id?: string }>();
  const { items, addToCart } = useMarketplace();

  const activeCollection = id ? marketCollections.find((collection) => collection.id === id) : null;
  const sourceItems = items.length ? items : fallbackMarketplaceItems;

  const filteredItems = activeCollection
    ? sourceItems.filter((item) => collectionToCategories[activeCollection.id]?.includes(item.category))
    : sourceItems;

  return (
    <MarketLayout
      title={activeCollection ? activeCollection.title : 'Curated Collections'}
      subtitle={activeCollection ? activeCollection.description : 'Collection rails for vertical browsing and shelf bundles.'}
    >
      <MarketCollectionRail />
      {activeCollection ? (
        <p className="ow-market-subcopy">
          Showing items from <strong>{activeCollection.title}</strong>. <Link to="/marketplace/collections">View all collections</Link>
        </p>
      ) : null}
      <MarketShelf items={filteredItems} emptyCopy="No items available in this collection." onAddToCart={addToCart} />
    </MarketLayout>
  );
};

export default MarketplaceCollections;
