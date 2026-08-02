import React, { useState, useEffect } from 'react';
import { conversations } from '../services/api';
import { CheckCircle, XCircle } from 'lucide-react';

export default function Conversations({ profileId }) {
  const [list, setList] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => { if (profileId) load(); }, [profileId]);

  async function load() {
    const data = await conversations.list(profileId);
    setList(data);
  }

  return (
    <div className="p-6" style={{ maxWidth: 1200 }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Conversations</h1>
      <p className="text-secondary mb-6">Transcript and outcome log per session.</p>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 24 }}>
        <div className="card" style={{ padding: 12, maxHeight: 'calc(100vh - 200px)', overflow: 'auto' }}>
          <div className="card-title" style={{ marginBottom: 12, fontSize: 13 }}>Sessions</div>
          {list.map(sess => (
            <button
              key={sess.session_id}
              onClick={() => setSelected(sess)}
              style={{
                width: '100%',
                textAlign: 'left',
                padding: '10px 12px',
                borderRadius: 8,
                border: '1px solid',
                borderColor: selected?.session_id === sess.session_id ? 'var(--color-accent)' : 'transparent',
                background: selected?.session_id === sess.session_id ? 'rgba(124,58,237,0.1)' : 'transparent',
                cursor: 'pointer',
                marginBottom: 4,
              }}
            >
              <div className="flex justify-between items-center">
                <span className="text-xs text-muted">{sess.session_id}</span>
                {sess.outcome === 'abandoned' ? (
                  <XCircle size={12} className="text-danger" />
                ) : (
                  <CheckCircle size={12} className="text-success" />
                )}
              </div>
              <div className="text-xs text-secondary mt-1">
                {new Date(sess.started_at).toLocaleString()}
              </div>
            </button>
          ))}
        </div>

        <div>
          {selected ? (
            <div className="card">
              <div className="card-header">
                <div>
                  <div className="card-title">{selected.session_id}</div>
                  <div className="text-xs text-muted">Outcome: <span className={selected.outcome === 'abandoned' ? 'text-danger' : 'text-success'}>{selected.outcome}</span></div>
                </div>
              </div>
              <div className="flex flex-col gap-3">
                {selected.transcript.map((turn, i) => (
                  <div key={i} className={`flex ${turn.speaker === 'weaver' ? 'justify-start' : 'justify-end'}`}>
                    <div 
                      className="p-3 rounded-lg" 
                      style={{ 
                        maxWidth: '80%',
                        background: turn.speaker === 'weaver' ? 'var(--color-surface-raised)' : 'var(--color-accent)',
                        color: turn.speaker === 'weaver' ? 'var(--color-text)' : 'white',
                        borderRadius: turn.speaker === 'weaver' ? '4px 12px 12px 12px' : '12px 4px 12px 12px',
                      }}
                    >
                      <div className="text-xs opacity-70 mb-1" style={{ textTransform: 'capitalize' }}>{turn.speaker}</div>
                      <div className="text-sm">{turn.text}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 pt-4" style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
                <div className="flex gap-4 text-xs text-muted">
                  <span>Stages: {selected.stage_transitions.join(' &rarr; ')}</span>
                  <span>Actions: {selected.actions_approved}/{selected.actions_requested} approved</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="card text-secondary text-center p-12">Select a conversation to view transcript.</div>
          )}
        </div>
      </div>
    </div>
  );
}
