import React, { useEffect, useState } from 'react';
import { fieldMaintenance } from '../services/api';
import { RefreshCw, ShieldCheck, AlertTriangle } from 'lucide-react';

const EXAMPLE = JSON.stringify([
  {
    product_id: 'product-1',
    product_url: '/products/example',
    title: 'Example Product',
    sku: 'SKU-1',
    price: '$69.00',
    availability: 'available',
    page_structure_hash: 'page-structure-hash',
    verified: true,
    targets: [
      {
        target_id: 'product-1-price',
        target_type: 'price',
        selector: '[data-price]',
        exists: true,
        unique_match: true,
        verified: true,
        evidence: ['live DOM match'],
      },
    ],
  },
], null, 2);

export default function FieldMaintenance() {
  const [status, setStatus] = useState(null);
  const [json, setJson] = useState(EXAMPLE);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => { load(); }, []);

  async function load() {
    try { setStatus(await fieldMaintenance.status()); } catch (error) { setMessage(error.message); }
  }

  async function runCycle() {
    setBusy(true);
    setMessage('');
    try {
      const observations = JSON.parse(json);
      await fieldMaintenance.cycle(observations);
      await load();
      setMessage('Maintenance cycle completed. Unverified drift remains non-authoritative.');
    } catch (error) {
      setMessage(error.message || 'Maintenance cycle failed.');
    } finally { setBusy(false); }
  }

  return (
    <div className="p-6" style={{ maxWidth: 1000 }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Field Site World Maintenance</h1>
      <p className="text-secondary mb-6">Observe known commercial surfaces, reverify affected targets, and publish only verified state.</p>

      {status && (
        <div className="card mb-4">
          <div className="card-header">
            <div className="card-title flex items-center gap-2"><ShieldCheck size={16} /> Capability status</div>
            <button className="btn btn-ghost text-xs" onClick={load}><RefreshCw size={12} /> Refresh</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
            <div><div className="text-xs text-muted">Products tracked</div><div className="font-medium">{status.products_tracked}</div></div>
            <div><div className="text-xs text-muted">Authoritative</div><div className="font-medium">{status.authoritative_products}</div></div>
            <div><div className="text-xs text-muted">Targets tracked</div><div className="font-medium">{status.targets_tracked}</div></div>
            <div><div className="text-xs text-muted">Mode</div><div className="font-medium">{status.execution_mode}</div></div>
          </div>
          {status.deep_rescan_required && <div className="text-warning text-sm mt-4 flex items-center gap-2"><AlertTriangle size={14} /> Deep rescan required for unresolved structural drift.</div>}
        </div>
      )}

      <div className="card">
        <div className="card-title mb-2">Explicit maintenance cycle</div>
        <p className="text-secondary text-sm mb-3">Paste observations from the approved Dock/browser adapter. This lane never changes products or prices.</p>
        <textarea className="input" style={{ minHeight: 300, fontFamily: 'monospace', fontSize: 12 }} value={json} onChange={e => setJson(e.target.value)} />
        <div className="flex items-center gap-3 mt-3">
          <button className="btn btn-primary" onClick={runCycle} disabled={busy}><RefreshCw size={14} /> {busy ? 'Running…' : 'Run Product Delta + Reverification'}</button>
          {message && <span className="text-secondary text-sm">{message}</span>}
        </div>
      </div>
    </div>
  );
}
