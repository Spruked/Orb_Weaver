import React, { useState, useEffect } from 'react';
import { appearance } from '../services/api';
import { Lock, Upload, RotateCcw, Eye, Palette, Sun, Box, Image, Move, CheckCircle } from 'lucide-react';

export default function AppearanceMotion({ profileId }) {
  const [config, setConfig] = useState(null);
  const [skins, setSkins] = useState([]);
  const [activeSkinId, setActiveSkinId] = useState(null);
  const [editingSkin, setEditingSkin] = useState(null);
  const [newSkinName, setNewSkinName] = useState('');
  const [motionState, setMotionState] = useState('idle');
  const [saved, setSaved] = useState(false);

  useEffect(() => { if (profileId) load(); }, [profileId]);

  async function load() {
    const data = await appearance.get(profileId);
    setConfig(data);
    setActiveSkinId(data.active_skin_id);
    setSkins(data.skins || []);
    setMotionState(data.motion_preview_state || 'idle');
  }

  async function saveAppearance(patch) {
    const updated = { ...config, ...patch };
    await appearance.update(profileId, updated);
    setConfig(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  }

  async function activateSkin(skinId) {
    await appearance.activateSkin(profileId, skinId);
    setActiveSkinId(skinId);
    load();
  }

  async function restoreFactory() {
    await appearance.restoreFactory(profileId);
    load();
  }

  async function createSkin() {
    if (!newSkinName.trim()) return;
    const skin = {
      name: newSkinName,
      base_color: '#7c3aed',
      secondary_color: '#a78bfa',
      shell_type: 'sphere',
      lighting: {
        ambient: '#1a1a2e',
        glow_color: '#7c3aed',
        glow_intensity: 0.6,
        rim_light: '#a78bfa',
        rim_intensity: 0.3,
      },
      size_scale: 1.0,
      decals: [],
    };
    await appearance.createSkin(profileId, skin);
    setNewSkinName('');
    load();
  }

  async function updateSkin(skinId, patch) {
    const skin = skins.find(s => s.id === skinId);
    if (!skin) return;
    const updated = { ...skin, ...patch };
    await appearance.updateSkin(profileId, skinId, updated);
    setSkins(skins.map(s => s.id === skinId ? updated : s));
    if (activeSkinId === skinId) {
      setConfig({ ...config, active_skin_id: skinId });
    }
  }

  async function setMotionPreview(state) {
    await appearance.setMotionPreview(profileId, state);
    setMotionState(state);
  }

  if (!config) return <div className="p-6 text-secondary">Select a profile first.</div>;

  const activeSkin = skins.find(s => s.id === activeSkinId) || skins[0];

  const motionStates = [
    { id: 'idle', label: 'Idle', desc: 'Waiting state' },
    { id: 'listening', label: 'Listening', desc: 'Receiving input' },
    { id: 'thinking', label: 'Thinking', desc: 'Processing' },
    { id: 'speaking', label: 'Speaking', desc: 'Delivering response' },
    { id: 'pointer', label: 'Pointer', desc: 'Guiding to target' },
    { id: 'success', label: 'Success', desc: 'Action completed' },
    { id: 'warning', label: 'Warning', desc: 'Attention needed' },
    { id: 'failure', label: 'Failure', desc: 'Error state' },
  ];

  const shellTypes = ['sphere', 'orb', 'hexagon', 'diamond', 'ring'];

  return (
    <div className="p-6" style={{ maxWidth: 1200 }}>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Appearance & Motion</h1>
          <p className="text-secondary">Skin editor, motion preview, and visual doctrine.</p>
        </div>
        {saved && (
          <span className="badge badge-healthy flex items-center gap-1">
            <CheckCircle size={12} /> Saved
          </span>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Left column: Live ORB Preview + Skin Gallery */}
        <div className="flex flex-col gap-4">
          {/* Live ORB Preview */}
          <div className="card" style={{ minHeight: 300, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
            <div className="card-title" style={{ position: 'absolute', top: 16, left: 16 }}>Live Preview</div>

            {/* ORB render */}
            <div style={{
              width: 140,
              height: 140,
              borderRadius: activeSkin?.shell_type === 'hexagon' ? '20%' : activeSkin?.shell_type === 'diamond' ? '10%' : '50%',
              background: `radial-gradient(circle at 30% 30%, ${activeSkin?.base_color || '#7c3aed'}, ${activeSkin?.secondary_color || '#a78bfa'}88)`,
              boxShadow: `0 0 ${40 * (activeSkin?.lighting?.glow_intensity || 0.6)}px ${activeSkin?.lighting?.glow_color || '#7c3aed'}`,
              border: `2px solid ${activeSkin?.lighting?.rim_light || '#a78bfa'}`,
              transform: `scale(${activeSkin?.size_scale || 1})`,
              transition: 'all 0.5s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              animation: motionState === 'listening' ? 'pulse 1.5s infinite' : motionState === 'thinking' ? 'spin 3s linear infinite' : motionState === 'speaking' ? 'pulse 0.8s infinite' : 'none',
            }}>
              <span style={{ color: 'white', fontSize: 12, fontWeight: 600, opacity: 0.8 }}>ORB</span>
            </div>

            <div className="text-xs text-muted mt-4" style={{ textTransform: 'capitalize' }}>
              {activeSkin?.name} &bull; {motionState}
            </div>
          </div>

          {/* Skin Gallery */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Skin Gallery</div>
              <button className="btn btn-ghost text-xs" onClick={restoreFactory}>
                <RotateCcw size={12} /> Factory
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 12 }}>
              {skins.map(skin => (
                <button
                  key={skin.id}
                  onClick={() => activateSkin(skin.id)}
                  style={{
                    padding: 12,
                    borderRadius: 8,
                    border: `2px solid ${activeSkinId === skin.id ? 'var(--color-accent)' : 'var(--color-border)'}`,
                    background: activeSkinId === skin.id ? 'rgba(124,58,237,0.1)' : 'var(--color-surface-raised)',
                    cursor: 'pointer',
                    textAlign: 'center',
                  }}
                >
                  <div style={{
                    width: 40,
                    height: 40,
                    borderRadius: '50%',
                    background: `radial-gradient(circle at 30% 30%, ${skin.base_color}, ${skin.secondary_color}88)`,
                    margin: '0 auto 8px',
                    boxShadow: `0 0 12px ${skin.lighting?.glow_color || skin.base_color}`,
                  }} />
                  <div className="text-xs font-medium">{skin.name}</div>
                  {skin.is_factory && <span className="badge badge-locked mt-1" style={{ fontSize: 9 }}>Factory</span>}
                </button>
              ))}
            </div>

            <div className="flex gap-2">
              <input 
                className="input text-sm" 
                placeholder="New skin name..."
                value={newSkinName}
                onChange={e => setNewSkinName(e.target.value)}
              />
              <button className="btn btn-primary text-xs" onClick={createSkin}>
                <Palette size={12} /> Create
              </button>
            </div>
          </div>
        </div>

        {/* Right column: Skin Editor + Motion Preview */}
        <div className="flex flex-col gap-4">
          {/* Skin Editor */}
          {activeSkin && !activeSkin.is_factory && (
            <div className="card">
              <div className="card-title mb-4">Edit Skin: {activeSkin.name}</div>

              <div className="flex flex-col gap-3">
                <div>
                  <label className="text-xs text-muted">Base Color</label>
                  <div className="flex gap-2 items-center">
                    <input 
                      type="color" 
                      value={activeSkin.base_color}
                      onChange={e => updateSkin(activeSkin.id, { base_color: e.target.value })}
                      style={{ width: 40, height: 32, border: 'none', borderRadius: 6, cursor: 'pointer' }}
                    />
                    <span className="text-sm">{activeSkin.base_color}</span>
                  </div>
                </div>

                <div>
                  <label className="text-xs text-muted">Secondary Color</label>
                  <div className="flex gap-2 items-center">
                    <input 
                      type="color" 
                      value={activeSkin.secondary_color}
                      onChange={e => updateSkin(activeSkin.id, { secondary_color: e.target.value })}
                      style={{ width: 40, height: 32, border: 'none', borderRadius: 6, cursor: 'pointer' }}
                    />
                    <span className="text-sm">{activeSkin.secondary_color}</span>
                  </div>
                </div>

                <div>
                  <label className="text-xs text-muted">Shell Type</label>
                  <div className="flex gap-2">
                    {shellTypes.map(type => (
                      <button
                        key={type}
                        onClick={() => updateSkin(activeSkin.id, { shell_type: type })}
                        className="btn text-xs"
                        style={{
                          background: activeSkin.shell_type === type ? 'var(--color-accent)' : undefined,
                          color: activeSkin.shell_type === type ? 'white' : undefined,
                        }}
                      >
                        {type}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-xs text-muted">Size Scale</label>
                  <input 
                    type="range" min={0.5} max={3} step={0.1}
                    value={activeSkin.size_scale}
                    onChange={e => updateSkin(activeSkin.id, { size_scale: parseFloat(e.target.value) })}
                  />
                  <span className="text-xs text-muted">{activeSkin.size_scale}x</span>
                </div>

                <div>
                  <label className="text-xs text-muted">Glow Color</label>
                  <div className="flex gap-2 items-center">
                    <input 
                      type="color" 
                      value={activeSkin.lighting?.glow_color || '#7c3aed'}
                      onChange={e => updateSkin(activeSkin.id, { lighting: { ...activeSkin.lighting, glow_color: e.target.value } })}
                      style={{ width: 40, height: 32, border: 'none', borderRadius: 6, cursor: 'pointer' }}
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs text-muted">Glow Intensity</label>
                  <input 
                    type="range" min={0} max={1} step={0.1}
                    value={activeSkin.lighting?.glow_intensity || 0.6}
                    onChange={e => updateSkin(activeSkin.id, { lighting: { ...activeSkin.lighting, glow_intensity: parseFloat(e.target.value) } })}
                  />
                </div>

                <div>
                  <label className="text-xs text-muted">Rim Light</label>
                  <div className="flex gap-2 items-center">
                    <input 
                      type="color" 
                      value={activeSkin.lighting?.rim_light || '#a78bfa'}
                      onChange={e => updateSkin(activeSkin.id, { lighting: { ...activeSkin.lighting, rim_light: e.target.value } })}
                      style={{ width: 40, height: 32, border: 'none', borderRadius: 6, cursor: 'pointer' }}
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs text-muted">Rim Intensity</label>
                  <input 
                    type="range" min={0} max={1} step={0.1}
                    value={activeSkin.lighting?.rim_intensity || 0.3}
                    onChange={e => updateSkin(activeSkin.id, { lighting: { ...activeSkin.lighting, rim_intensity: parseFloat(e.target.value) } })}
                  />
                </div>

                <div>
                  <label className="text-xs text-muted">Texture Scale</label>
                  <input 
                    type="range" min={0.1} max={5} step={0.1}
                    value={activeSkin.texture_scale || 1}
                    onChange={e => updateSkin(activeSkin.id, { texture_scale: parseFloat(e.target.value) })}
                  />
                </div>
              </div>
            </div>
          )}

          {activeSkin?.is_factory && (
            <div className="card">
              <div className="flex items-center gap-3 p-3 rounded-md" style={{ background: 'var(--color-surface-raised)' }}>
                <Lock size={16} className="text-accent" />
                <div>
                  <div className="text-sm font-medium">Factory Skin</div>
                  <div className="text-xs text-muted">Immutable fallback — cannot be edited. Create a new skin to customize.</div>
                </div>
              </div>
            </div>
          )}

          {/* Motion Preview */}
          <div className="card">
            <div className="card-title mb-4">Motion Preview</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6 }}>
              {motionStates.map(state => (
                <button
                  key={state.id}
                  onClick={() => setMotionPreview(state.id)}
                  className="btn text-xs"
                  style={{
                    padding: '8px 4px',
                    background: motionState === state.id ? 'var(--color-accent)' : undefined,
                    color: motionState === state.id ? 'white' : undefined,
                  }}
                >
                  <div className="font-medium">{state.label}</div>
                  <div className="text-xs opacity-70">{state.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Speed Doctrine */}
          <div className="card">
            <div className="card-title mb-4">Speed Doctrine</div>
            <div className="flex flex-col gap-2">
              {[
                { name: 'glide', desc: 'Default smooth motion. Used always unless visitor signals urgency or runtime failure.' },
                { name: 'brisk', desc: 'Faster motion. Only on explicit visitor urgency signal.' },
                { name: 'urgent', desc: 'Rapid motion. Only on genuine runtime failure requiring attention.' },
              ].map(d => (
                <div key={d.name} className="flex items-center gap-3 p-3 rounded-md" style={{ background: 'var(--color-surface-raised)' }}>
                  <Lock size={14} className="text-accent" />
                  <div>
                    <div className="text-sm font-medium" style={{ textTransform: 'capitalize' }}>{d.name}</div>
                    <div className="text-xs text-muted">{d.desc}</div>
                  </div>
                  <span className="badge badge-locked" style={{ marginLeft: 'auto' }}>Doctrine</span>
                </div>
              ))}
            </div>
          </div>

          {/* Clumsy Motion */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Clumsy Motion Pack</div>
              <div 
                className={`toggle ${config.clumsy_motion_enabled ? 'active' : ''}`}
                onClick={() => saveAppearance({ clumsy_motion_enabled: !config.clumsy_motion_enabled })}
              />
            </div>
            <div className="text-xs text-muted mt-2">
              Auto-suppresses on Checkout/Payment/Signature/Confirmation/destructive controls.
            </div>
            {config.clumsy_motion_enabled && (
              <div className="mt-3">
                <label className="text-xs text-muted">Intensity</label>
                <input 
                  type="range" min={0} max={1} step={0.1}
                  value={config.clumsy_intensity}
                  onChange={e => saveAppearance({ clumsy_intensity: parseFloat(e.target.value) })}
                />
              </div>
            )}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.05); opacity: 0.8; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
