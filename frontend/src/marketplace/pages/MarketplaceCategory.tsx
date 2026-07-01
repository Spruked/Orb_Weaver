import React from 'react';
import { useParams } from 'react-router-dom';
import MarketLayout from '../components/MarketLayout';
import MarketShelf from '../components/MarketShelf';
import { useMarketplace } from '../hooks/useMarketplace';

const MarketplaceCategory: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { items, setCategory, selectedCategory, addToCart, loading } = useMarketplace();

  React.useEffect(() => {
    if (id) {
      setCategory(id);
    }
  }, [id, setCategory]);

  return (
    <MarketLayout
      title={`Category shelf: ${id || selectedCategory}`}
      subtitle="Focused browse view for one catalog section."
    >
      {loading ? (
        <div className="ow-market-empty">Loading category shelf...</div>
      ) : (
        <MarketShelf items={items} emptyCopy="No items in this category yet." onAddToCart={addToCart} />
      )}
    </MarketLayout>
  );
};

export default MarketplaceCategory;
