import React from 'react';
import { useSearchParams } from 'react-router-dom';
import MarketLayout from '../components/MarketLayout';
import MarketShelf from '../components/MarketShelf';
import { useMarketplace } from '../hooks/useMarketplace';

const MarketplaceSearch: React.FC = () => {
  const [params, setParams] = useSearchParams();
  const initialQuery = params.get('q') || '';
  const { items, searchTerm, setSearchTerm, addToCart } = useMarketplace();

  React.useEffect(() => {
    if (!searchTerm && initialQuery) {
      setSearchTerm(initialQuery);
    }
  }, [initialQuery, searchTerm, setSearchTerm]);

  const handleSubmit: React.FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const query = String(formData.get('q') || '');
    setSearchTerm(query);
    setParams(query ? { q: query } : {});
  };

  return (
    <MarketLayout
      title="Search the ORB market index"
      subtitle="Use product names, index codes, and feature terms to find listings quickly."
    >
      <form className="ow-market-search" onSubmit={handleSubmit}>
        <input name="q" defaultValue={initialQuery} placeholder="Search by code, name, or feature" />
        <button type="submit">Search</button>
      </form>
      <MarketShelf items={items} emptyCopy="No matching catalog entries." onAddToCart={addToCart} />
    </MarketLayout>
  );
};

export default MarketplaceSearch;
