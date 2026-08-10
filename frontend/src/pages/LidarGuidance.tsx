import React, { useEffect } from 'react';
import PublicHeader from '../components/PublicHeader';
import PublicFooter from '../components/PublicFooter';
import '../landing/Landing.css';

const LidarGuidance: React.FC = () => {
  useEffect(() => {
    document.title = 'LiDAR-Inspired Guidance | ORB Weaver';
  }, []);

  return (
    <main className="ow-cut-page">
      <div className="ow-cut-grid" />
      <div className="ow-cut-noise" />
      
      <PublicHeader theme="dark" />

      <div style={{ position: 'relative', zIndex: 2 }}>
        {/* Hero Section - Light */}
        <section style={{
          minHeight: '85vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(180deg, #f5f1e8 0%, #e8e2d5 50%, #1a2332 100%)',
          padding: 'clamp(60px, 10vh, 120px) clamp(20px, 6vw, 80px)'
        }}>
          <div style={{ maxWidth: '1200px', width: '100%', textAlign: 'center' }}>
            <p style={{
              fontSize: '13px',
              fontWeight: 700,
              letterSpacing: '0.22em',
              color: '#c4d82e',
              marginBottom: '20px'
            }}>TECHNICAL DIFFERENTIATOR</p>
            <h1 style={{
              fontSize: 'clamp(48px, 7vw, 82px)',
              fontWeight: 900,
              lineHeight: 0.98,
              letterSpacing: '-0.03em',
              color: '#1a1a1a',
              marginBottom: '24px'
            }}>
              LiDAR-Inspired Guidance Mesh™
            </h1>
            <p style={{
              fontSize: 'clamp(22px, 2.5vw, 34px)',
              lineHeight: 1.3,
              color: '#4a5568',
              fontWeight: 600,
              maxWidth: '800px',
              margin: '0 auto'
            }}>
              Instant Spatial Awareness. Precision Without Constant Reasoning.
            </p>
          </div>
        </section>

        {/* Dark Content Section */}
        <section style={{
          background: 'linear-gradient(180deg, #1a2332 0%, #0a1120 100%)',
          padding: 'clamp(60px, 8vh, 100px) clamp(20px, 6vw, 80px)'
        }}>
          <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'grid', gap: 'clamp(40px, 6vh, 80px)' }}>
            
          <div className="rounded-2xl border border-red-500/30 bg-red-950/20 p-6" style={{ padding: 'clamp(24px, 4vw, 48px)' }}>
            <h2 className="text-2xl font-bold text-white mt-0">The Problem</h2>
            <p className="text-lg text-slate-200">
              Traditional website assistants repeatedly ask the same question:
            </p>
            <blockquote className="border-l-4 border-red-500 pl-4 italic text-xl text-slate-300">
              "Where am I now?"
            </blockquote>
            <p className="text-slate-200">
              Every time the visitor scrolls...<br />
              Every time the page changes...<br />
              Every time a pointer moves...<br />
              <strong className="text-white">the AI often has to re-evaluate the interface.</strong>
            </p>
            <p className="text-slate-200">
              That creates latency.
            </p>
            <p className="text-white font-semibold text-lg">
              ORB Weaver approaches the problem differently.
            </p>
          </div>

          <div className="rounded-2xl border border-cyan-300/20 bg-white/[0.05] p-6 md:p-8">
            <h2 className="text-3xl font-bold text-white mt-0">Inspired by 2D LiDAR</h2>
            <p className="text-lg text-slate-200">
              Autonomous robots don't repeatedly guess where obstacles are.
            </p>
            <p className="text-lg text-slate-200">
              They rapidly build a <strong className="text-cyan-300">two-dimensional spatial model</strong> of their environment.
            </p>
            <p className="text-lg text-slate-200">
              Once that map exists, navigation becomes dramatically faster.
            </p>
            <p className="text-xl text-white font-semibold">
              ORB Weaver applies the same principle to websites.
            </p>
            <p className="text-lg text-slate-200">
              Instead of continuously reasoning over the entire DOM, it constructs a <strong className="text-cyan-300">lightweight spatial guidance model</strong> that understands the location and relationship of interactive elements across the page.
            </p>
            <p className="text-xl text-cyan-200 font-semibold">
              The result is an environment the ORB already knows.
            </p>
          </div>

          <div className="rounded-2xl border border-cyan-300/20 bg-slate-900/60 p-6 md:p-8">
            <h2 className="text-3xl font-bold text-white mt-0">The Website Guidance Map</h2>
            <p className="text-lg text-slate-200">
              Each verified control becomes part of a continuously updated spatial model.
            </p>
            <p className="text-sm font-semibold tracking-wide text-cyan-300 uppercase">Examples include:</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 my-6">
              {['Buttons', 'Navigation links', 'Forms', 'Inputs', 'Menus', 'Dialogs', 'Cards', 'Checkout controls', 'Calls to action', 'Anchors', 'Scroll regions'].map((item) => (
                <div key={item} className="rounded-lg border border-cyan-500/20 bg-cyan-950/30 px-3 py-2 text-center text-sm text-cyan-100">
                  {item}
                </div>
              ))}
            </div>
            <p className="text-lg text-white font-semibold">
              Rather than searching for these elements during every interaction, the ORB references its existing guidance map.
            </p>
          </div>

          <div className="rounded-2xl border border-green-500/30 bg-green-950/20 p-6 md:p-8">
            <h2 className="text-3xl font-bold text-white mt-0">Reduced Latency</h2>
            
            <div className="grid md:grid-cols-2 gap-6 my-8">
              <div className="rounded-xl border border-red-500/30 bg-red-950/20 p-5">
                <p className="text-sm font-bold uppercase tracking-wide text-red-300 mb-4">Traditional Guidance</p>
                <div className="space-y-3 text-slate-200">
                  <div>Visitor asks ↓</div>
                  <div>Reason over DOM ↓</div>
                  <div>Search page ↓</div>
                  <div>Locate control ↓</div>
                  <div>Verify ↓</div>
                  <div className="text-white font-semibold">Guide</div>
                </div>
              </div>

              <div className="rounded-xl border border-green-500/30 bg-green-950/30 p-5">
                <p className="text-sm font-bold uppercase tracking-wide text-green-300 mb-4">ORB Weaver</p>
                <div className="space-y-3 text-slate-200">
                  <div>Visitor asks ↓</div>
                  <div className="text-cyan-300 font-semibold">Consult Guidance Map ↓</div>
                  <div>Verify Position ↓</div>
                  <div className="text-white font-semibold">Guide</div>
                </div>
              </div>
            </div>

            <p className="text-lg text-white">
              Because the spatial model already exists, <strong className="text-green-300">response time is significantly reduced</strong> while maintaining precision.
            </p>
          </div>

          <div className="rounded-2xl border border-cyan-300/20 bg-white/[0.05] p-6 md:p-8">
            <h2 className="text-3xl font-bold text-white mt-0">Precision Guidance</h2>
            <p className="text-lg text-slate-200">
              The guidance model understands more than coordinates.
            </p>
            <p className="text-lg text-slate-200">
              Each verified target contains contextual information such as:
            </p>
            <ul className="space-y-2 text-slate-200 text-lg">
              <li>• Screen position</li>
              <li>• Scroll offset</li>
              <li>• Parent relationships</li>
              <li>• Route ownership</li>
              <li>• Visibility</li>
              <li>• Verification status</li>
              <li>• Allowed actions</li>
              <li>• Pointer confidence</li>
              <li>• Interaction history</li>
            </ul>
            <p className="text-lg text-white font-semibold mt-6">
              This allows the ORB to guide visitors accurately without repeatedly rediscovering the interface.
            </p>
          </div>

          <div className="rounded-2xl border border-cyan-300/20 bg-slate-900/60 p-6 md:p-8">
            <h2 className="text-3xl font-bold text-white mt-0">Continuous Adaptation</h2>
            <p className="text-lg text-slate-200">
              The guidance model is not static.
            </p>
            <p className="text-lg text-slate-200">
              As pages change through responsive layouts, dynamic rendering, or content updates, <strong className="text-cyan-300">the map refreshes only the affected regions</strong> rather than rebuilding everything.
            </p>
            <p className="text-lg text-white font-semibold">
              This minimizes computation while preserving accuracy.
            </p>
          </div>

          <div className="rounded-2xl border border-cyan-300/30 bg-cyan-950/20 p-6 md:p-8">
            <h2 className="text-3xl font-bold text-white mt-0">Why LiDAR?</h2>
            <p className="text-lg text-slate-200">
              The inspiration is architectural rather than literal.
            </p>
            <div className="grid md:grid-cols-2 gap-6 my-6">
              <div className="text-center p-4 rounded-lg border border-cyan-500/30 bg-cyan-950/40">
                <p className="text-sm uppercase tracking-wide text-cyan-300 mb-2">LiDAR</p>
                <p className="text-xl font-semibold text-white">Measures physical space</p>
              </div>
              <div className="text-center p-4 rounded-lg border border-cyan-500/30 bg-cyan-950/40">
                <p className="text-sm uppercase tracking-wide text-cyan-300 mb-2">ORB Weaver</p>
                <p className="text-xl font-semibold text-white">Maps interactive space</p>
              </div>
            </div>
            <p className="text-lg text-slate-200">
              Both systems answer the same fundamental question:
            </p>
            <blockquote className="border-l-4 border-cyan-500 pl-4 italic text-xl text-cyan-200">
              "Where is the next verified destination?"
            </blockquote>
          </div>

          <div className="rounded-2xl border border-green-500/30 bg-green-950/20 p-6 md:p-8">
            <h2 className="text-3xl font-bold text-white mt-0">Faster Guidance</h2>
            <p className="text-lg text-slate-200 mb-6">
              The LiDAR-inspired guidance layer enables:
            </p>
            <div className="grid md:grid-cols-2 gap-4">
              {[
                'Lower response latency',
                'Reduced DOM traversal',
                'Faster pointer guidance',
                'Smoother Point-and-Ping interaction',
                'More stable navigation',
                'Better continuity between visitor actions',
                'Less repeated reasoning',
                'Higher confidence in destination verification'
              ].map((benefit) => (
                <div key={benefit} className="flex items-start space-x-3">
                  <div className="text-green-400 text-xl">✓</div>
                  <div className="text-slate-200">{benefit}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-cyan-300/30 bg-gradient-to-br from-cyan-950/40 to-blue-950/40 p-8 md:p-10">
            <h2 className="text-3xl font-bold text-white mt-0">An Operational Navigation Layer</h2>
            <p className="text-lg text-slate-200">
              The guidance model becomes another strand in the weave.
            </p>
            <div className="space-y-4 my-6 text-lg">
              <p className="text-slate-200">
                <strong className="text-cyan-300">Knowledge</strong> tells the ORB <strong className="text-white">what</strong> the visitor needs.
              </p>
              <p className="text-slate-200">
                The <strong className="text-cyan-300">spatial guidance model</strong> tells it <strong className="text-white">where</strong> that next step is.
              </p>
            </div>
            <p className="text-xl text-white font-semibold">
              Together they allow the Website ORB to understand both meaning and location—responding with context and guiding with precision.
            </p>
          </div>
          
          </div>
        </section>
      </div>
      <PublicFooter />
    </main>
  );
};

export default LidarGuidance;
