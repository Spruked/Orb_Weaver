import React, { useState, useEffect } from 'react';
import { diagnostics } from '../services/api';
import { AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';

export default function Diagnostics() {
  const [health, setHealth] = useState(null);
  const [pointer, setPointer] = useState(null);
  const [issues, setIssues] = useState([]);
  const [recovering, setRecovering] = useState(false);

  useEffect(() => { load(); }, []);

  async function load() {
    const [h, p, i] = await Promise.all([
      diagnostics.health(),
      diagnostics.pointer(),
      diagnostics.issues(),
    ]);
    setHealth(h);
    setPointer(p);
    setIssues(i);
  }

  async function runRecovery() {
    setRecovering(true);
    await diagnostics.recovery();
    await load();
    setRecovering(false);
  }

  return (
    <div className="p-6" style={{ maxWidth: 900 }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Diagnostics</h1>
      <p className="text-secondary mb-6">Operational health, gateway lanes, and pointer status.</p>

      <div className="flex flex-col gap-4">
        {health && (
          <div className="card">
            <div className="card-title mb-4">System Health</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
              <div className="p-3 rounded-md" style={{ background: 'var(--color-surface-raised)' }}>
                <div className="text-xs text-muted mb-1">Overall</div>
                <div className={`flex items-center gap-2 ${health.overall === 'healthy' ? 'text-success' : health.overall === 'degraded' ? 'text-warning' : 'text-danger'}`}>
                  {health.overall === 'healthy' ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
                  <span className="font-medium" style={{ textTransform: 'capitalize' }}>{health.overall}</span>
                </div>
              </div>
              <div className="p-3 rounded-md" style={{ background: 'var(--color-surface-raised)' }}>
                <div className="text-xs text-muted mb-1">Pointer Confidence</div>
                <div className="font-medium text-accent">{Math.round(health.pointer_confidence * 100)}%</div>
              </div>
              <div className="p-3 rounded-md" style={{ background: 'var(--color-surface-raised)' }}>
                <div className="text-xs text-muted mb-1">Gateway Lanes</div>
                <div className="font-medium text-success">{health.checks.gateway_lanes_up}/{health.checks.gateway_lanes_total} up</div>
              </div>
            </div>
          </div>
        )}

        {pointer && (
          <div className="card">
            <div className="card-header">
              <div className="card-title">Pointer Targets</div>
              <button className="btn btn-primary text-xs" onClick={runRecovery} disabled={recovering}>
                <RefreshCw size={12} /> Run Recovery
              </button>
            </div>
            <div className="flex flex-col gap-2">
              {pointer.targets.map(t => (
                <div key={t.id} className="flex items-center gap-3 p-2 rounded-md" style={{ background: 'var(--color-surface-raised)' }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: 
                    t.status === 'verified' ? 'var(--color-success)' : 
                    t.status === 'new' ? 'var(--color-info)' : 
                    t.status === 'recovered' ? 'var(--color-warning)' : 'var(--color-danger)'
                  }} />
                  <div style={{ flex: 1 }}>
                    <div className="text-sm font-medium">{t.id}</div>
                    <div className="text-xs text-muted">{t.selector}</div>
                  </div>
                  <span className="badge" style={{ 
                    background: t.confidence > 0.9 ? 'rgba(34,197,94,0.15)' : t.confidence > 0.7 ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
                    color: t.confidence > 0.9 ? 'var(--color-success)' : t.confidence > 0.7 ? 'var(--color-warning)' : 'var(--color-danger)'
                  }}>
                    {Math.round(t.confidence * 100)}%
                  </span>
                  <span className="badge" style={{ textTransform: 'capitalize' }}>{t.status}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {issues.length > 0 && (
          <div className="card">
            <div className="card-title mb-4">Active Issues</div>
            <div className="flex flex-col gap-2">
              {issues.map(issue => (
                <div key={issue.id} className="flex items-start gap-3 p-3 rounded-md" style={{ background: 'var(--color-surface-raised)' }}>
                  <AlertTriangle size={16} className={issue.severity === 'critical' ? 'text-danger' : 'text-warning'} style={{ marginTop: 2 }} />
                  <div style={{ flex: 1 }}>
                    <div className="text-sm font-medium">{issue.message}</div>
                    {issue.remediation && <div className="text-xs text-muted mt-1">{issue.remediation}</div>}
                  </div>
                  {issue.auto_resolvable && <span className="badge badge-healthy">Auto-fix</span>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
