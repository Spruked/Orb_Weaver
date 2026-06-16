import React from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, Filter, Sparkles } from 'lucide-react';
import PublicNav from '../../components/PublicNav';
import PublicFooter from '../../components/PublicFooter';
import { api, MarketplaceItem } from '../../services/api';
import './marketplace.css';

const fallbackItems: MarketplaceItem[] = [
  {
    item_id: 'orb_basic_visitor',
    market_index_code: 'ORB-MKT.110.01',
    name: 'Basic Visitor ORB',
    price: '$488.88',
    badge: 'Entry product',
    description: 'Website visitor guide installed from Orb Weaver scan intelligence.',
    features: ['Basic website ORB install', 'Initial target map', 'Customer account access', 'Basic Dock access for desktop path'],
    href: '/signup',
    category: 'orbs',
    tier_access: ['basic', 'premium', 'platinum'],
    rights_status: 'first_party',
    rarity: 'standard',
    sku: 'orb-basic-visitor',
    purchasable: true,
  },
  {
    item_id: 'orb_enhanced_website',
    market_index_code: 'ORB-MKT.210.02',
    name: 'Enhanced Website ORB',
    price: '$988',
    badge: 'Stronger routing',
    description: 'More precise service, department, form, and content-path guidance.',
    features: ['Enhanced scan mapping', 'Priority target routing', 'FAQ/content extraction', 'More launch scan credits'],
    href: '/signup',
    category: 'orbs',
    tier_access: ['premium', 'platinum'],
    rights_status: 'first_party',
    rarity: 'standard',
    sku: 'orb-enhanced-website',
    purchasable: true,
  },
  {
    item_id: 'orb_premium_website',
    market_index_code: 'ORB-MKT.310.03',
    name: 'Premium Website ORB',
    price: '$1,988+',
    badge: 'Premium build',
    description: 'Branded ORB with semantic intelligence, custom behavior, and premium upgrade path.',
    features: ['Branded ORB styling', 'Semantic knowledge graph', 'Custom behavior profile', 'Premium diagnostics eligible'],
    href: '/signup',
    category: 'orbs',
    tier_access: ['premium', 'platinum'],
    rights_status: 'licensed_required',
    rarity: 'standard',
    sku: 'orb-premium-website',
    purchasable: true,
  },
  {
    item_id: 'orb_skin_pack_starter',
    market_index_code: 'ORB-MKT.331.12',
    name: 'ORB Skin Packs',
    price: 'From $2.49',
    badge: 'Studio assets',
    description: 'Purchase skins and visual packs for owned ORBs, rebuilt from Skin Studio into Orb Weaver.',
    features: ['Single skins', 'Creator bundles', 'Premium skin previews', 'Studio export configs'],
    href: '/orb-studio',
    category: 'skins',
    tier_access: ['premium', 'platinum'],
    rights_status: 'licensed_required',
    rarity: 'standard',
    sku: 'orb-skin-pack-starter',
    purchasable: true,
  },
  {
    item_id: 'orb_diagnostics_pack',
    market_index_code: 'ORB-MKT.510.02',
    name: 'Diagnostics Pack',
    price: 'Add-on',
    badge: 'Health checks',
    description: 'Run deeper install checks for Website ORB, Desktop ORB, Dock Station, and GA4/tag readiness.',
    features: ['Website ORB check', 'Desktop ORB check', 'Dock Station check', 'Config validation'],
    href: '/diagnostics',
    category: 'diagnostics',
    tier_access: ['premium', 'platinum'],
    rights_status: 'first_party',
    rarity: 'standard',
    sku: 'orb-diagnostics-pack',
    purchasable: true,
  },
  {
    item_id: 'orb_scan_bundle_10',
    market_index_code: 'ORB-MKT.610.01',
    name: 'Scan Bundles',
    price: 'From $19',
    badge: 'Credits',
    description: 'Add maintenance, verification, and preflight scan credits to an Orb Weaver account.',
    features: ['5, 10, 25, or 50 scans', 'Maintenance scans', 'Report refreshes', 'Client project history'],
    href: '/signup',
    category: 'credits',
    tier_access: ['basic', 'premium', 'platinum'],
    rights_status: 'first_party',
    rarity: 'standard',
    sku: 'orb-scan-bundle-10',
    purchasable: true,
  },
  {
    item_id: 'orb_behavior_voice_pack',
    market_index_code: 'ORB-MKT.710.09',
    name: 'Behavior / Voice Packs',
    price: 'Planned',
    badge: 'Upgrade packs',
    description: 'Future add-ons for greeting behavior, visitor routing, industry responses, and voice style.',
    features: ['Greeting behavior', 'Industry packs', 'Voice/motion packs', 'Live handoff tuning'],
    href: '/orb-studio',
    category: 'packs',
    tier_access: ['premium', 'platinum'],
    rights_status: 'licensed_required',
    rarity: 'limited',
    sku: null,
    purchasable: false,
  },
];

const MarketplacePage: React.FC = () => {
  const [items, setItems] = React.useState<MarketplaceItem[]>(fallbackItems);
  const [category, setCategory] = React.useState('all');
  const [feedback, setFeedback] = React.useState('');
  const [activeSku, setActiveSku] = React.useState('');

  React.useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const payload = await api.listMarketplaceItems(category === 'all' ? undefined : category);
        if (!cancelled && payload.length) {
          setItems(payload);
        }
      } catch {
        if (!cancelled) {
          setItems(category === 'all' ? fallbackItems : fallbackItems.filter((item) => item.category === category));
        }
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [category]);

  const addToCart = async (item: MarketplaceItem) => {
    if (!item.sku || !item.purchasable) {
      setFeedback(`${item.name} is cataloged but not purchasable yet.`);
      return;
    }

    setActiveSku(item.sku);
    setFeedback('');
    try {
      await api.upsertCartItem({ sku: item.sku, quantity: 1 });
      setFeedback(`${item.name} added to cart.`);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Unable to add item to cart.');
    } finally {
      setActiveSku('');
    }
  };

  const categories = ['all', 'orbs', 'skins', 'dock', 'diagnostics', 'credits', 'packs'];

  return (
    <div className="ow-marketplace-shell">
      <PublicNav />
      <main className="ow-marketplace-main">
        <header className="ow-marketplace-hero">
          <div className="ow-marketplace-hero-copy">
            <p className="ow-marketplace-kicker"><BookOpen size={14} /> ORB Marketplace Library</p>
            <h1>Comfortable browsing, library-grade indexing.</h1>
            <p>
              A standalone-ready marketplace section for ORB skins, packs, diagnostics, and deployable products.
              Each item carries a market index code so the catalog can evolve into its own site later.
            </p>
          </div>
          <div className="ow-marketplace-hero-card">
            <p>Doctrine</p>
            <h2>ORB-MKT Index</h2>
            <span>Library-style classification for products and collectibles.</span>
          </div>
        </header>

        <section className="ow-marketplace-toolbar">
          <div className="ow-marketplace-filter-label"><Filter size={14} /> Browse shelf</div>
          <div className="ow-marketplace-filters">
            {categories.map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => setCategory(key)}
                className={category === key ? 'active' : ''}
              >
                {key === 'all' ? 'All Shelves' : key}
              </button>
            ))}
          </div>
          <Link to="/cart" className="ow-marketplace-cart-link">Open Cart</Link>
        </section>

        {feedback && (
          <div className="ow-marketplace-feedback">
            <Sparkles size={14} />
            <span>{feedback}</span>
          </div>
        )}

        <section className="ow-marketplace-grid">
          {items.map((item) => (
            <article key={item.item_id} className="ow-marketplace-card">
              <div className="ow-marketplace-card-head">
                <p>{item.badge}</p>
                <span>{item.price}</span>
              </div>
              <h3>{item.name}</h3>
              <small>{item.market_index_code}</small>
              <p className="ow-marketplace-description">{item.description}</p>
              <ul>
                {item.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
              <div className="ow-marketplace-meta">
                <span>{item.rights_status}</span>
                <span>{item.rarity}</span>
              </div>
              <div className="ow-marketplace-actions">
                <button
                  type="button"
                  disabled={!item.sku || !item.purchasable || activeSku === item.sku}
                  onClick={() => addToCart(item)}
                >
                  {activeSku === item.sku ? 'Adding...' : (item.purchasable ? 'Add to Cart' : 'Planned')}
                </button>
                <Link to={item.href}>View</Link>
              </div>
            </article>
          ))}
        </section>
      </main>
      <PublicFooter />
    </div>
  );
};

export default MarketplacePage;
