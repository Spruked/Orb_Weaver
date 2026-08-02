import React, { useState, useEffect } from 'react';
import { statistics } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function Statistics({ profileId }) {
  const [stats, setStats] = useState([]);

  useEffect(() => { if (profileId) load(); }, [profileId]);

  async function load() {
    const data = await statistics.list(profileId);
    setStats(data);
  }

  if (!stats.length) return <div className="p-6 text-secondary">No statistics available.</div>;

  const latest = stats[stats.length - 1];
  const chartData = stats.map(s => ({
    period: new Date(s.period_end).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    conversations: s.conversations_total,
    journeys: s.guided_journeys_completed,
    approved: s.actions_approved,
  }));

  const pipelineData = [
    { name: 'Speech Rec', value: latest.avg_speech_recognition_ms },
    { name: 'LLM', value: latest.avg_llm_response_ms },
    { name: 'TTS', value: latest.avg_tts_generation_ms },
  ];

  return (
    <div className="p-6" style={{ maxWidth: 1200 }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Statistics</h1>
      <p className="text-secondary mb-6">Visitor experience metrics and pipeline performance.</p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        {[
          { label: 'Conversations', value: latest.conversations_total },
          { label: 'Journeys Completed', value: latest.guided_journeys_completed },
          { label: 'Pointer Success', value: `${Math.round(latest.pointer_success_rate * 100)}%` },
          { label: 'Cache Hit', value: `${latest.cache_hit_percent}%` },
        ].map(m => (
          <div key={m.label} className="card" style={{ textAlign: 'center' }}>
            <div className="text-xs text-muted mb-1">{m.label}</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--color-accent-light)' }}>{m.value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div className="card">
          <div className="card-title mb-4">Conversations vs Journeys</div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <XAxis dataKey="period" tick={{ fontSize: 12, fill: '#8a8aa0' }} />
              <YAxis tick={{ fontSize: 12, fill: '#8a8aa0' }} />
              <Tooltip contentStyle={{ background: '#1a1a25', border: '1px solid #2a2a3a', borderRadius: 8 }} />
              <Bar dataKey="conversations" fill="#7c3aed" radius={[4, 4, 0, 0]} />
              <Bar dataKey="journeys" fill="#22c55e" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="card-title mb-4">Pipeline Latency (ms)</div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={pipelineData}>
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#8a8aa0' }} />
              <YAxis tick={{ fontSize: 12, fill: '#8a8aa0' }} />
              <Tooltip contentStyle={{ background: '#1a1a25', border: '1px solid #2a2a3a', borderRadius: 8 }} />
              <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card mt-4">
        <div className="card-title mb-4">Action Governance</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          <div className="p-3 rounded-md" style={{ background: 'var(--color-surface-raised)' }}>
            <div className="text-xs text-muted mb-1">Requested</div>
            <div style={{ fontSize: 24, fontWeight: 600 }}>{latest.actions_requested}</div>
          </div>
          <div className="p-3 rounded-md" style={{ background: 'var(--color-surface-raised)' }}>
            <div className="text-xs text-muted mb-1">Approved</div>
            <div style={{ fontSize: 24, fontWeight: 600, color: 'var(--color-warning)' }}>{latest.actions_approved}</div>
          </div>
          <div className="p-3 rounded-md" style={{ background: 'var(--color-surface-raised)' }}>
            <div className="text-xs text-muted mb-1">Verified</div>
            <div style={{ fontSize: 24, fontWeight: 600, color: 'var(--color-success)' }}>{latest.actions_verified}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
