import React, { useState, useEffect } from 'react';
import { behavior } from '../services/api';
import { Lock } from 'lucide-react';

export default function BehaviorPersonality({ profileId }) {
  const [personality, setPersonality] = useState(null);
  const [directives, setDirectives] = useState([]);

  useEffect(() => { if (profileId) load(); }, [profileId]);

  async function load() {
    const [p, d] = await Promise.all([
      behavior.getPersonality(profileId),
      behavior.getDirectives(profileId),
    ]);
    setPersonality(p);
    setDirectives(d);
  }

  async function savePersonality(patch) {
    const updated = { ...personality, ...patch };
    await behavior.updatePersonality(profileId, updated);
    setPersonality(updated);
  }

  if (!personality) return <div className="p-6 text-secondary">Select a profile first.</div>;

  const sliders = [
    { key: 'conviction', label: 'Conviction', max: 0.75, note: 'Capped at 0.75 under tension' },
    { key: 'warmth', label: 'Warmth' },
    { key: 'humor', label: 'Humor', note: 'Requires evidence when enabled' },
    { key: 'directness', label: 'Directness' },
  ];

  return (
    <div className="p-6" style={{ maxWidth: 900 }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Behavior & Personality</h1>
      <p className="text-secondary mb-6">Weaver's voice, tone, and stage directives.</p>

      <div className="flex flex-col gap-4">
        <div className="card">
          <div className="card-title mb-4">Personality Blend</div>
          <div className="flex flex-col gap-4">
            {sliders.map(s => (
              <div key={s.key}>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium">{s.label}</span>
                  <span className="text-sm text-accent">{personality[s.key]}</span>
                </div>
                <input 
                  type="range" min={0} max={1} step={0.05}
                  value={personality[s.key]}
                  onChange={e => savePersonality({ [s.key]: parseFloat(e.target.value) })}
                />
                {s.note && <div className="text-xs text-muted mt-1">{s.note}</div>}
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-title mb-4">Doctrine Flags</div>
          <div className="flex flex-col gap-3">
            {[
              { key: 'first_person_mandatory', label: 'First-person enforcement', desc: 'Weaver narrates his own actions, never a third-person voice.' },
              { key: 'anti_decoration_rule', label: 'Anti-decoration rule', desc: 'Weaver may not remain visually active but functionally silent after a screen stabilizes.' },
              { key: 'humor_requires_evidence', label: 'Humor requires evidence', desc: 'Jokes suppressed without supporting evidence.' },
            ].map(flag => (
              <div key={flag.key} className="flex items-center gap-3 p-3 rounded-md" style={{ background: 'var(--color-surface-raised)' }}>
                <Lock size={16} className="text-accent" />
                <div style={{ flex: 1 }}>
                  <div className="text-sm font-medium">{flag.label}</div>
                  <div className="text-xs text-muted">{flag.desc}</div>
                </div>
                <span className="badge badge-locked">Locked</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-title mb-4">Stage Directives</div>
          <div className="flex flex-col gap-2">
            {directives.map((d, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-md" style={{ background: 'var(--color-surface-raised)' }}>
                <div className="badge" style={{ background: 'var(--color-accent)', color: 'white', minWidth: 100, justifyContent: 'center' }}>
                  {d.stage}
                </div>
                <div className="text-sm">{d.emphasis}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
