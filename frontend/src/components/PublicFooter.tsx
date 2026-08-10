import React from 'react';

const PublicFooter: React.FC = () => {
  return (
    <footer style={{
      position: 'relative',
      zIndex: 10,
      borderTop: '1px solid rgba(108, 215, 238, 0.15)',
      background: 'rgba(3, 8, 16, 0.95)',
      backdropFilter: 'blur(12px)',
      padding: 'clamp(40px, 6vh, 80px) clamp(20px, 4vw, 54px) clamp(30px, 4vh, 50px)',
      color: '#b8cad4'
    }}>
      <div style={{
        maxWidth: '1400px',
        margin: '0 auto',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: 'clamp(30px, 5vw, 60px)'
      }}>
        {/* Product Column */}
        <div>
          <h3 style={{
            fontSize: '13px',
            fontWeight: 800,
            letterSpacing: '0.12em',
            color: '#6cd7ee',
            textTransform: 'uppercase',
            marginBottom: '16px'
          }}>Product</h3>
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <a href="/features" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>Features</a>
            <a href="/lidar-guidance" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>LiDAR Guidance</a>
            <a href="/how-it-works" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>How It Works</a>
            <a href="/security" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>Security</a>
            <a href="/now/desktop-orb" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>Desktop ORB</a>
            <a href="/marketplace" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>Marketplace</a>
          </nav>
        </div>

        {/* Company Column */}
        <div>
          <h3 style={{
            fontSize: '13px',
            fontWeight: 800,
            letterSpacing: '0.12em',
            color: '#6cd7ee',
            textTransform: 'uppercase',
            marginBottom: '16px'
          }}>Company</h3>
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <a href="/founding-beta" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>Founding Beta</a>
            <a href="/investor-contact" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>Investors</a>
            <a href="https://campaign.orbweaver.spruked.com" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>Campaign Portal</a>
            <a href="https://spruked.com" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>Spruked</a>
          </nav>
        </div>

        {/* Resources Column */}
        <div>
          <h3 style={{
            fontSize: '13px',
            fontWeight: 800,
            letterSpacing: '0.12em',
            color: '#6cd7ee',
            textTransform: 'uppercase',
            marginBottom: '16px'
          }}>Resources</h3>
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <a href="/preflight" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>Preflight Scanner</a>
            <a href="/login" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>Login</a>
            <a href="/sitemap.xml" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>Sitemap</a>
          </nav>
        </div>

        {/* Legal Column */}
        <div>
          <h3 style={{
            fontSize: '13px',
            fontWeight: 800,
            letterSpacing: '0.12em',
            color: '#6cd7ee',
            textTransform: 'uppercase',
            marginBottom: '16px'
          }}>Legal</h3>
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <a href="/privacy" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>Privacy Policy</a>
            <a href="/terms" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>Terms of Service</a>
            <a href="/weaving" style={{ color: 'inherit', textDecoration: 'none', fontSize: '14px' }}>Practice of Weaving</a>
          </nav>
        </div>
      </div>

      {/* Copyright Bar */}
      <div style={{
        marginTop: 'clamp(40px, 6vh, 70px)',
        paddingTop: '24px',
        borderTop: '1px solid rgba(108, 215, 238, 0.1)',
        textAlign: 'center',
        fontSize: '13px',
        color: '#7a8c98'
      }}>
        <p style={{ margin: 0 }}>
          © 2026 Pro Prime Series. All rights reserved.
        </p>
      </div>
    </footer>
  );
};

export default PublicFooter;
