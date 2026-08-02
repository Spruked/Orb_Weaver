import React, { useState, useEffect } from 'react';
import { profiles } from '../services/api';
import { GitBranch, Upload, RotateCcw, AlertTriangle, CheckCircle } from 'lucide-react';

export default function Overview({ onSelectProfile, activeProfile }) {
  const [list, setList] = useState([]);
  const [selected, setSelected] = useState(null);
  const [diff, setDiff] = useState(null);
  const [versions, setVersions] = useState([]);
  const [publishNote, setPublishNote] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => { loadProfiles(); }, []);

  async function loadProfiles() {
    const data = await profiles.list();
    setList(data);
    if (data.length && !activeProfile) {
      handleSelect(data[0]);
    } else if (activeProfile) {
      const p = data.find(x => x.id === activeProfile);
      if (p) handleSelect(p);
    }
  }

  async function handleSelect(p) {
    setSelected(p);
    onSelectProfile(p.id);
    const [d, v] = await Promise.all([
      profiles.diff(p.id),
      profiles.versions(p.id),
    ]);
    setDiff(d);
    setVersions(v);
  }

  async function handlePublish() {
    setLoading(true);
    await profiles.publish(selected.id, publishNote);
    setPublishNote('');
    await loadProfiles();
    setLoading(false);
  }

  async function handleRestore(version) {
    if (!confirm(`Restore version ${version}?`)) return;
    await profiles.restore(selected.id, version);
    await loadProfiles();
  }

  const current = selected || list[0];

  return (
    <div className="p-6" style={{ maxWidth: 1200 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Overview</h1>
          <p className="text-secondary">Profile management, versioning, and publication</p>
        </div>
        {current && (
          <div className="flex gap-2">
            <span className={`badge badge-${current.state}`}>{current.state}</span>
            <span className="badge" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-secondary)' }}>
              v{current.version}
            </span>
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 24 }}>
        <div className="card" style={{ padding: 12 }}>
          <div className="card-title" style={{ marginBottom: 12, fontSize: 13 }}>Profiles</div>
          {list.map(p => (
            <button
              key={p.id}
              onClick={() => handleSelect(p)}
              style={{
                width: '100%',
                textAlign: 'left',
                padding: '10px 12px',
                borderRadius: 8,
                border: '1px solid',
                borderColor: selected?.id === p.id ? 'var(--color-accent)' : 'transparent',
                background: selected?.id === p.id ? 'rgba(124,58,237,0.1)' : 'transparent',
                cursor: 'pointer',
                marginBottom: 4,
              }}
            >
              <div style={{ fontWeight: 500, fontSize: 13 }}>{p.display_name}</div>
              <div className="text-xs text-muted">{p.channel} &bull; {p.state}</div>
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-4">
          {current && (
            <div className="card" style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
              <div>
                <div className="text-xs text-muted mb-2">POINTER CONFIDENCE</div>
                <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--color-accent-light)' }}>91%</div>
              </div>
              <div style={{ width: 1, height: 40, background: 'var(--color-border)' }} />
              <div>
                <div className="text-xs text-muted mb-2">MODEL REACHABILITY</div>
                <div className="flex items-center gap-2 text-success">
                  <CheckCircle size={16} /> Healthy
                </div>
              </div>
              <div style={{ width: 1, height: 40, background: 'var(--color-border)' }} />
              <div>
                <div className="text-xs text-muted mb-2">VOICE REACHABILITY</div>
                <div className="flex items-center gap-2 text-success">
                  <CheckCircle size={16} /> Healthy
                </div>
              </div>
            </div>
          )}

          {current && diff && (
            <div className="card">
              <div className="card-header">
                <div className="card-title flex items-center gap-2">
                  <GitBranch size={16} />
                  Draft vs Published
                </div>
                {diff.has_diff && (
                  <span className="badge badge-warning flex items-center gap-1">
                    <AlertTriangle size={12} /> Unpublished changes
                  </span>
                )}
              </div>

              {diff.has_diff ? (
                <div className="flex flex-col gap-3">
                  <div style={{ background: 'var(--color-surface-raised)', padding: 12, borderRadius: 8 }}>
                    <div className="text-xs text-muted mb-2">CHANGES</div>
                    {diff.changes.map((c, i) => (
                      <div key={i} className="text-sm" style={{ padding: '4px 0' }}>&bull; {c}</div>
                    ))}
                  </div>
                  <div className="flex gap-3 items-end">
                    <div style={{ flex: 1 }}>
                      <label className="text-xs text-muted">Publish note</label>
                      <input 
                        className="input" 
                        value={publishNote} 
                        onChange={e => setPublishNote(e.target.value)}
                        placeholder="What changed in this version?"
                      />
                    </div>
                    <button className="btn btn-success" onClick={handlePublish} disabled={loading}>
                      <Upload size={14} /> Publish
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-secondary text-sm">No unpublished changes. Profile is up to date.</div>
              )}
            </div>
          )}

          {versions.length > 0 && (
            <div className="card">
              <div className="card-title" style={{ marginBottom: 12 }}>Version History</div>
              <table className="table">
                <thead>
                  <tr>
                    <th>Version</th>
                    <th>State</th>
                    <th>Summary</th>
                    <th>Date</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {versions.slice(0, 10).map(v => (
                    <tr key={v.version}>
                      <td>v{v.version}</td>
                      <td><span className={`badge badge-${v.state}`}>{v.state}</span></td>
                      <td className="text-secondary">{v.change_summary || '—'}</td>
                      <td className="text-secondary">{new Date(v.created_at).toLocaleDateString()}</td>
                      <td>
                        {v.state === 'published' && (
                          <button className="btn btn-ghost text-xs" onClick={() => handleRestore(v.version)}>
                            <RotateCcw size={12} /> Restore
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
