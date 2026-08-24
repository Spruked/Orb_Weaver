import React from 'react';
import { Link } from 'react-router-dom';
import MarketCollectionRail from '../components/MarketCollectionRail';
import MarketLayout from '../components/MarketLayout';
import MarketShelf from '../components/MarketShelf';
import { useMarketplace } from '../hooks/useMarketplace';

const MarketplaceHome: React.FC = () => {
  const {
    items,
    categories,
    selectedCategory,
    setCategory,
    setSearchTerm,
    addToCart,
    message,
    error,
    loading,
  } = useMarketplace();

  const featuredItems = React.useMemo(() => {
    const skinItems = items.filter((item) => item.category === 'skins');
    const prioritizedSkins = [...skinItems].sort((a, b) => Number(Boolean(b.image_src)) - Number(Boolean(a.image_src)));
    const source = prioritizedSkins.length ? prioritizedSkins : items;
    return source.slice(0, 3);
  }, [items]);
  const shelfByCategory = (category: string) => items.filter((item) => item.category === category);
  const randomizedMorbs = React.useMemo(() => {
    const ordered = [...shelfByCategory('morbs')];
    for (let index = ordered.length - 1; index > 0; index -= 1) {
      const nextIndex = Math.floor(Math.random() * (index + 1));
      [ordered[index], ordered[nextIndex]] = [ordered[nextIndex], ordered[index]];
    }
    return ordered;
  }, [items]);

  const onSearchSubmit: React.FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const query = String(formData.get('q') || '').trim();
    setSearchTerm(query);
  };

  return (
    <MarketLayout
      title="ORB Marketplace Library"
      subtitle="Browse Website ORBs, MORBs, intelligence packs, skins, diagnostics, and collector assets."
    >
      <section className="ow-market-toolbar">
        <form className="ow-market-search-index" onSubmit={onSearchSubmit}>
          <label htmlFor="market-index-query">Index Search</label>
          <input id="market-index-query" name="q" placeholder="Search call number, product, or chapter" />
          <button type="submit">Search Catalog</button>
        </form>
        <div className="ow-market-chip-row">
          {categories.slice(0, 6).map((category) => (
            <button key={category} type="button" className={selectedCategory === category ? 'active' : ''} onClick={() => setCategory(category)}>
              {category === 'all' ? 'Featured collection' : category}
            </button>
          ))}
        </div>
        <Link to="/marketplace/search" className="ow-market-link-button">Advanced Search</Link>
      </section>

      {message ? <div className="ow-market-feedback">{message}</div> : null}
      {error ? <div className="ow-market-warning">{error}</div> : null}

      <MarketCollectionRail />

      {loading ? (
        <div className="ow-market-empty">Loading catalog shelves...</div>
      ) : (
        <>
          <section className="ow-market-section">
            <div className="ow-market-section-head">
              <h2>Featured Shelf</h2>
              <p>Curated picks from the market index.</p>
            </div>
            <MarketShelf items={featuredItems} emptyCopy="No featured items available." onAddToCart={addToCart} />
          </section>

          <section className="ow-market-section">
            <div className="ow-market-section-head">
              <h2>Website ORB Packages</h2>
              <p>Deployable visitor and premium website ORBs.</p>
            </div>
            <MarketShelf items={shelfByCategory('orbs')} emptyCopy="No Website ORB packages found." onAddToCart={addToCart} />
          </section>

          <section className="ow-market-section">
            <div className="ow-market-section-head">
              <h2>MORBs</h2>
              <p>Micro ORBs a Prime ORB deploys for focused visitor guidance.</p>
            </div>
            <MarketShelf items={randomizedMorbs} emptyCopy="No MORBs available." onAddToCart={addToCart} />
          </section>

          <section className="ow-market-section">
            <div className="ow-market-section-head">
              <h2>Website Weave Packs</h2>
              <p>Structure, meaning, design, commerce, workflows, and documents.</p>
            </div>
            <MarketShelf items={shelfByCategory('website-weave')} emptyCopy="No Website Weave Packs available." onAddToCart={addToCart} />
          </section>

          <section className="ow-market-section">
            <div className="ow-market-section-head">
              <h2>Navigation Intelligence</h2>
              <p>Governed LiDAR and pointer intelligence for verified guidance.</p>
            </div>
            <MarketShelf items={shelfByCategory('navigation-intelligence')} emptyCopy="No navigation intelligence packs available." onAddToCart={addToCart} />
          </section>

          <section className="ow-market-section">
            <div className="ow-market-section-head">
              <h2>ORB Intelligence</h2>
              <p>Site World and Vault intelligence for the ORB cognitive model.</p>
            </div>
            <MarketShelf items={shelfByCategory('orb-intelligence')} emptyCopy="No ORB intelligence packs available." onAddToCart={addToCart} />
          </section>

          <section className="ow-market-section">
            <div className="ow-market-section-head">
              <h2>Integrity & Maintenance</h2>
              <p>Diagnostics, refresh, and ongoing monitoring for correct live behavior.</p>
            </div>
            <MarketShelf items={shelfByCategory('integrity-maintenance')} emptyCopy="No integrity packs available." onAddToCart={addToCart} />
          </section>

          <section className="ow-market-section">
            <div className="ow-market-section-head">
              <h2>Dock & Diagnostics</h2>
              <p>Desktop pairing, health checks, and runtime controls.</p>
            </div>
            <MarketShelf
              items={[...shelfByCategory('dock'), ...shelfByCategory('diagnostics')]}
              emptyCopy="No dock or diagnostics items found."
              onAddToCart={addToCart}
            />
          </section>

          <section className="ow-market-section">
            <div className="ow-market-section-head">
              <h2>Skins & Behavior Packs</h2>
              <p>Ready-to-install ORB looks and behavior upgrades.</p>
            </div>
            <MarketShelf items={[...shelfByCategory('skins'), ...shelfByCategory('packs')]} emptyCopy="No skins or behavior packs found." onAddToCart={addToCart} />
          </section>

        </>
      )}
    </MarketLayout>
  );
};

export default MarketplaceHome;
