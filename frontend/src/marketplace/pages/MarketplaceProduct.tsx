import React from 'react';
import { Link, useParams } from 'react-router-dom';
import MarketLayout from '../components/MarketLayout';
import MarketIndexCode from '../components/MarketIndexCode';
import { useMarketplace } from '../hooks/useMarketplace';

const BASIC_ORB_INFOGRAPHIC_SRC = '/marketplace-basic-orb-infographic.png';

type AuthoritySection = {
  heading: string;
  body?: string;
  bullets?: string[];
};

type AuthorityProductContent = {
  slug: string;
  itemId: string;
  heroSummary: string;
  launchPriceLabel?: string;
  ctaLabel: string;
  sections: AuthoritySection[];
  faq: Array<{ question: string; answer: string }>;
};

const AUTHORITY_PRODUCTS: AuthorityProductContent[] = [
  {
    slug: 'basic-visitor-orb',
    itemId: 'orb_basic_visitor',
    heroSummary: 'One-time website ORB installation for visitor guidance.',
    launchPriceLabel: 'Launch Price: $488.88',
    ctaLabel: 'Start Installation',
    sections: [
      {
        heading: 'What It Is',
        body: 'A one-time installed website guide ORB powered by Orb Weaver scan intelligence to help visitors reach the right destination faster.',
      },
      {
        heading: 'Who It Is For',
        bullets: [
          'Small business websites',
          'Dealer websites',
          'Local service sites',
          'Farms, shops, consultants, and public-facing pages',
        ],
      },
      {
        heading: 'What Is Included',
        bullets: [
          'Basic website ORB install',
          'Initial target map',
          'Customer account access',
          'Basic appearance setup',
          'Standard handoff behavior',
        ],
      },
      {
        heading: 'How It Works',
        bullets: [
          'Guides visitors to pages, forms, phone numbers, departments, and live chat',
          'Uses Orb Weaver scan intelligence to map intent and destination paths',
          'Does not replace your sales team',
          'Does not block the customer, it adds a guide layer',
        ],
      },
      {
        heading: 'Installation and Delivery',
        body: 'Delivery is a one-time installation process with handoff behavior configured to match your site structure and customer journey goals.',
      },
      {
        heading: 'Maintenance and Scan Allowance',
        body: 'No monthly SaaS fee. Optional annual maintenance is available for ongoing scan refreshes and behavior tuning.',
      },
      {
        heading: 'Upgrade Path',
        body: 'Upgrade to Enhanced Website ORB for deeper routing precision and additional intelligence mapping.',
      },
      {
        heading: 'Example Use Cases',
        bullets: [
          'Guide visitors from homepage to financing/contact forms',
          'Route service seekers to department-specific pages',
          'Reduce drop-off before key conversion steps',
        ],
      },
    ],
    faq: [
      {
        question: 'Is there a monthly subscription?',
        answer: 'No. This is a one-time installed ORB with optional annual maintenance.',
      },
      {
        question: 'Can we upgrade later?',
        answer: 'Yes. Basic Visitor ORB can be upgraded into Enhanced and Premium tiers.',
      },
    ],
  },
  {
    slug: 'enhanced-website-orb',
    itemId: 'orb_enhanced_website',
    heroSummary: 'Advanced routing and intent mapping for higher-conversion website guidance.',
    launchPriceLabel: 'Launch Price: $988',
    ctaLabel: 'Start Enhanced Installation',
    sections: [
      {
        heading: 'What It Is',
        body: 'Enhanced Website ORB extends visitor guidance with deeper service and department precision across more intent paths.',
      },
      {
        heading: 'Who It Is For',
        bullets: [
          'Growing businesses with multiple departments',
          'Dealer and service-heavy websites',
          'Organizations with frequent visitor decision friction',
        ],
      },
      {
        heading: 'What Is Included',
        bullets: [
          'Enhanced scan mapping',
          'Priority target routing',
          'FAQ and content extraction',
          'Expanded launch scan credits',
        ],
      },
      {
        heading: 'How It Works',
        bullets: [
          'Builds a richer intent map across service and conversion flows',
          'Routes customers to the most relevant page or handoff point',
          'Supports clearer department-level guidance logic',
        ],
      },
      {
        heading: 'Installation and Delivery',
        body: 'Configured through a structured implementation process that includes route validation and conversion-focused handoff logic.',
      },
      {
        heading: 'Maintenance and Scan Allowance',
        body: 'No monthly SaaS fee. Optional annual maintenance adds scan refresh cycles and optimization iterations.',
      },
      {
        heading: 'Upgrade Path',
        body: 'Upgrade to Premium Website ORB for branded behavior profiles and semantic graph-driven intelligence.',
      },
      {
        heading: 'Example Use Cases',
        bullets: [
          'Segment visitors by intent before routing to forms',
          'Accelerate path-to-contact for high-value pages',
          'Improve service and sales department handoff clarity',
        ],
      },
    ],
    faq: [
      {
        question: 'Is this still one-time installed?',
        answer: 'Yes. Enhanced Website ORB is one-time installed with optional annual maintenance.',
      },
      {
        question: 'Does this include custom branding?',
        answer: 'Branding depth increases with Premium Website ORB, which is the next tier upgrade.',
      },
    ],
  },
  {
    slug: 'premium-website-orb',
    itemId: 'orb_premium_website',
    heroSummary: 'Authority-grade branded ORB with semantic intelligence and custom behavior design.',
    launchPriceLabel: 'Launch Price: $1,988+',
    ctaLabel: 'Start Premium Installation',
    sections: [
      {
        heading: 'What It Is',
        body: 'Premium Website ORB is the high-authority implementation tier for organizations that need custom behavior and branded intelligence design.',
      },
      {
        heading: 'Who It Is For',
        bullets: [
          'Multi-service organizations',
          'High-traffic websites with conversion bottlenecks',
          'Teams needing custom ORB behavior and premium routing precision',
        ],
      },
      {
        heading: 'What Is Included',
        bullets: [
          'Branded ORB styling',
          'Semantic knowledge graph',
          'Custom behavior profile',
          'Premium diagnostics eligibility',
        ],
      },
      {
        heading: 'How It Works',
        bullets: [
          'Combines scan intelligence with tailored behavior logic',
          'Routes visitors using structured semantic context',
          'Aligns ORB responses with business-specific conversion doctrine',
        ],
      },
      {
        heading: 'Installation and Delivery',
        body: 'Implemented as a guided premium deployment with branded integration, testing cycles, and launch handoff standards.',
      },
      {
        heading: 'Maintenance and Scan Allowance',
        body: 'No monthly SaaS fee. Optional annual maintenance provides continuing scan intelligence refresh and optimization support.',
      },
      {
        heading: 'Upgrade Path',
        body: 'Includes direct expansion path into enterprise-grade ORB programs, maintenance bundles, and custom scan operations.',
      },
      {
        heading: 'Example Use Cases',
        bullets: [
          'Cross-department visitor routing with branded interaction tone',
          'Complex service matrices with guided decision flows',
          'High-value lead path acceleration with custom handoff logic',
        ],
      },
    ],
    faq: [
      {
        question: 'Is Premium a subscription?',
        answer: 'No. Premium is a one-time installed authority package with optional annual maintenance.',
      },
      {
        question: 'Can this support custom enterprise behavior?',
        answer: 'Yes. Premium is the gateway to advanced and enterprise ORB behavior programs.',
      },
    ],
  },
];

const MarketplaceProduct: React.FC = () => {
  const { id, slug } = useParams<{ id: string; slug: string }>();
  const { items, addToCart } = useMarketplace();
  const [imageFailed, setImageFailed] = React.useState(false);

  const authorityConfig = AUTHORITY_PRODUCTS.find((entry) => entry.slug === slug);
  const item = authorityConfig
    ? items.find((entry) => entry.item_id === authorityConfig.itemId)
    : items.find((entry) => entry.item_id === id);
  const imageSrc = React.useMemo(() => {
    if (!item?.image_src) {
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
  }, [item?.image_src]);
  const isAuthorityPage = Boolean(authorityConfig && item);
  const isBasicVisitorAuthority = authorityConfig?.slug === 'basic-visitor-orb';
  const authorityPrice = React.useMemo(() => {
    if (!item) {
      return '$0';
    }
    const launchLabel = authorityConfig?.launchPriceLabel;
    if (launchLabel) {
      return launchLabel.replace(/^launch\s*price\s*:\s*/i, '').trim();
    }
    return item.price;
  }, [authorityConfig?.launchPriceLabel, item]);

  return (
    <MarketLayout
      title={item ? item.name : 'Product not found'}
      subtitle={isAuthorityPage ? authorityConfig?.heroSummary || '' : 'Detailed listing card for standalone-ready marketplace routes.'}
    >
      {!item ? (
        <div className="ow-market-empty">
          Product record was not found. <Link to="/marketplace">Return to marketplace</Link>.
        </div>
      ) : isAuthorityPage && authorityConfig ? (
        <article className="ow-market-product-authority">
          <header className="ow-market-authority-hero">
            <div className="ow-market-authority-copy">
              <p className="ow-market-chapter">Authority Product</p>
              <h2>{item.name}</h2>
              <div className="ow-market-authority-price-stack" aria-label="Purchase pricing">
                <p className="ow-market-authority-price">{authorityPrice}</p>
                <p className="ow-market-authority-price-tag">ONE-TIME PURCHASE</p>
                <p className="ow-market-authority-price-tag ow-market-authority-price-tag-muted">NO MONTHLY FEES</p>
              </div>
              <p className="ow-market-authority-summary">{authorityConfig.heroSummary}</p>
              <p className="ow-market-authority-note">Optional annual maintenance is available after initial install.</p>
            </div>
            {imageSrc && !imageFailed ? (
              <img
                className="ow-market-authority-image"
                src={imageSrc}
                alt={item.name}
                loading="lazy"
                onError={() => setImageFailed(true)}
              />
            ) : (
              <div className="ow-market-orb-preview ow-market-product-preview" aria-hidden="true" />
            )}
          </header>

          <div className="ow-market-authority-cta-row">
            <button className="ow-market-authority-primary-cta" type="button" disabled={!item.purchasable} onClick={() => addToCart(item)}>
              {item.purchasable ? `${authorityConfig.ctaLabel} - ${authorityPrice}` : 'Planned'}
            </button>
            <Link className="ow-market-authority-secondary-cta" to="/marketplace">Back to Marketplace</Link>
          </div>

          <section className="ow-market-authority-flow" aria-label="Visitor guidance funnel">
            <h3>Visitor Guidance Funnel</h3>
            {isBasicVisitorAuthority ? (
              <img
                className="ow-market-authority-flow-image"
                src={BASIC_ORB_INFOGRAPHIC_SRC}
                alt="Basic ORB visitor guidance flow infographic"
                loading="lazy"
              />
            ) : (
              <div className="ow-market-authority-flow-grid">
                <div className="ow-market-flow-step">Visitor Arrives</div>
                <div className="ow-market-flow-arrow" aria-hidden="true">↓</div>
                <div className="ow-market-flow-step">ORB Understands Intent</div>
                <div className="ow-market-flow-arrow" aria-hidden="true">↓</div>
                <div className="ow-market-flow-step">ORB Guides Visitor</div>
                <div className="ow-market-flow-arrow" aria-hidden="true">↓</div>
                <div className="ow-market-flow-step">Form / Call / Chat</div>
                <div className="ow-market-flow-arrow" aria-hidden="true">↓</div>
                <div className="ow-market-flow-step">Customer Reaches Destination</div>
              </div>
            )}
          </section>

          <section className="ow-market-authority-blocks">
            {authorityConfig.sections.map((section) => (
              <article key={section.heading} className="ow-market-authority-block">
                <h3>{section.heading}</h3>
                {section.body ? <p>{section.body}</p> : null}
                {section.bullets ? (
                  <ul className="ow-market-feature-list">
                    {section.bullets.map((bullet) => (
                      <li key={bullet}>{bullet}</li>
                    ))}
                  </ul>
                ) : null}
              </article>
            ))}
          </section>

          <section className="ow-market-authority-block">
            <h3>FAQ</h3>
            <div className="ow-market-authority-faq-list">
              {authorityConfig.faq.map((entry) => (
                <article key={entry.question} className="ow-market-authority-faq-item">
                  <h4>{entry.question}</h4>
                  <p>{entry.answer}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="ow-market-authority-block">
            <h3>Trust and Delivery Doctrine</h3>
            <p>
              Orb Weaver authority products are installed and delivered as controlled implementation packages. They are not SaaS lock-ins,
              and they preserve operator ownership with optional annual maintenance support.
            </p>
            <MarketIndexCode value={item.market_index_code} />
          </section>
        </article>
      ) : (
        <article className="ow-market-product-detail">
          <header>
            <p>{item.badge}</p>
            <span>{item.price}</span>
          </header>
          {imageSrc && !imageFailed ? (
            <img
              className="ow-market-product-image"
              src={imageSrc}
              alt={item.name}
              loading="lazy"
              onError={() => setImageFailed(true)}
            />
          ) : (
            <div className="ow-market-orb-preview ow-market-product-preview" aria-hidden="true" />
          )}
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
