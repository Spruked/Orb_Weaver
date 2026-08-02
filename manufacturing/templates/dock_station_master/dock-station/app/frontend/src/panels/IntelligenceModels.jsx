import React, { useState, useEffect } from 'react';
import { intelligence } from '../services/api';
import { 
  Server, CheckCircle, XCircle, Zap, RotateCcw, 
  Cpu, HardDrive, Thermometer, Settings, Activity,
  ChevronDown, ChevronUp, Play, AlertTriangle
} from 'lucide-react';

export default function IntelligenceModels({ profileId }) {
  const [config, setConfig] = useState(null);
  const [gateway, setGateway] = useState(null);
  const [expandedLane, setExpandedLane] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [testingLane, setTestingLane] = useState(null);
  const [restoring, setRestoring] = useState(false);

  useEffect(() => { if (profileId) load(); }, [profileId]);

  async function load() {
    const [c, g] = await Promise.all([
      intelligence.get(profileId),
      intelligence.gatewayHealth(),
    ]);
    setConfig(c);
    setGateway(g);
  }

  async function toggleLane(name) {
    const lanes = config.lanes.map(l => 
      l.name === name ? { ...l, enabled: !l.enabled } : l
    );
    await intelligence.update(profileId, { ...config, lanes });
    setConfig({ ...config, lanes });
  }

  async function updateLaneConfig(name, field, value) {
    const lanes = config.lanes.map(l => {
      if (l.name === name) {
        return { ...l, config: { ...l.config, [field]: value } };
      }
      return l;
    });
    await intelligence.update(profileId, { ...config, lanes });
    setConfig({ ...config, lanes });
  }

  async function activateLane(name) {
    await intelligence.activateLane(profileId, name);
    setConfig({ ...config, active_lane: name });
  }

  async function testConnection(name) {
    setTestingLane(name);
    const res = await intelligence.testLane(profileId, name);
    setTestResults(prev => ({ ...prev, [name]: { ...prev[name], connection: res } }));
    setTestingLane(null);
  }

  async function testResponse(name) {
    setTestingLane(name);
    const res = await intelligence.testLaneResponse(profileId, name);
    setTestResults(prev => ({ ...prev, [name]: { ...prev[name], response: res } }));
    setTestingLane(null);
  }

  async function restoreRecommended() {
    setRestoring(true);
    await intelligence.restoreRecommended(profileId);
    await load();
    setRestoring(false);
  }

  if (!config) return <div className="p-6 text-secondary">Select a profile first.</div>;

  const providers = [
    { id: 'llama.cpp', label: 'llama.cpp (Universal)' },
    { id: 'Aphrodite', label: 'Aphrodite (Scale)' },
    { id: 'TensorRT-LLM', label: 'TensorRT-LLM (Accelerated)' },
    { id: 'Ollama', label: 'Ollama (Fallback)' },
    { id: 'predicate-logic', label: 'Deterministic / No-LLM' },
  ];

  const quantizations = ['Q2_K', 'Q3_K_S', 'Q3_K_M', 'Q4_0', 'Q4_K_S', 'Q4_K_M', 'Q5_K_S', 'Q5_K_M', 'Q6_K', 'Q8_0', 'FP16', 'FP32'];
  const accelModes = ['cpu', 'cuda', 'rocm', 'metal', 'vulkan', 'tensorrt'];

  return (
    <div className="p-6" style={{ maxWidth: 1200 }}>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Intelligence & Models</h1>
          <p className="text-secondary">Inference gateway lanes, provider configuration, and runtime selection.</p>
        </div>
        <button className="btn btn-ghost text-xs" onClick={restoreRecommended} disabled={restoring}>
          <RotateCcw size={12} /> Restore Recommended
        </button>
      </div>

      {/* Active lane banner */}
      <div className="card mb-4" style={{ background: 'rgba(124,58,237,0.1)', borderColor: 'var(--color-accent)' }}>
        <div className="flex items-center gap-3">
          <Zap size={20} className="text-accent" />
          <div>
            <div className="text-sm font-medium">Active Lane: <span className="text-accent">{config.active_lane}</span></div>
            <div className="text-xs text-muted">
              {gateway?.routing_status} &bull; {config.fallback_enabled ? 'Fallback enabled' : 'No fallback'} 
              &bull; {config.deterministic_fallback ? 'Deterministic fallback active' : 'No deterministic lane'}
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        {config.lanes.map(lane => {
          const isExpanded = expandedLane === lane.name;
          const testRes = testResults[lane.name];

          return (
            <div key={lane.name} className="card" style={{ padding: isExpanded ? 20 : 16 }}>
              {/* Lane header */}
              <div className="flex items-center gap-3">
                <div 
                  className="toggle"
                  style={{ flexShrink: 0 }}
                  className={`toggle ${lane.enabled ? 'active' : ''}`}
                  onClick={() => toggleLane(lane.name)}
                />

                <div style={{ flex: 1 }}>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{lane.name}</span>
                    {config.active_lane === lane.name && (
                      <span className="badge" style={{ background: 'var(--color-accent)', color: 'white' }}>Active</span>
                    )}
                    {lane.is_deterministic && (
                      <span className="badge badge-locked">Deterministic</span>
                    )}
                    {lane.local ? (
                      <span className="badge badge-healthy">Local</span>
                    ) : (
                      <span className="badge badge-warning">API</span>
                    )}
                  </div>
                  <div className="text-xs text-muted">
                    {lane.config.provider} &bull; {lane.config.model_id} &bull; Priority {lane.priority}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {lane.config.healthy ? (
                    <CheckCircle size={14} className="text-success" />
                  ) : (
                    <XCircle size={14} className="text-danger" />
                  )}
                  <span className="text-xs text-secondary">
                    {lane.config.last_latency_ms ? `${lane.config.last_latency_ms}ms` : '—'}
                  </span>
                  <button 
                    className="btn btn-ghost text-xs" 
                    style={{ padding: '4px 8px' }}
                    onClick={() => setExpandedLane(isExpanded ? null : lane.name)}
                  >
                    {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>
              </div>

              {/* Expanded configuration */}
              {isExpanded && (
                <div className="mt-4 pt-4" style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    {/* Provider */}
                    <div>
                      <label className="text-xs text-muted">Provider</label>
                      <select 
                        className="select"
                        value={lane.config.provider}
                        onChange={e => updateLaneConfig(lane.name, 'provider', e.target.value)}
                      >
                        {providers.map(p => (
                          <option key={p.id} value={p.id}>{p.label}</option>
                        ))}
                      </select>
                    </div>

                    {/* Model ID */}
                    <div>
                      <label className="text-xs text-muted">Model ID</label>
                      <input 
                        className="input"
                        value={lane.config.model_id}
                        onChange={e => updateLaneConfig(lane.name, 'model_id', e.target.value)}
                      />
                    </div>

                    {/* Endpoint */}
                    <div>
                      <label className="text-xs text-muted">Endpoint</label>
                      <input 
                        className="input"
                        value={lane.config.endpoint}
                        onChange={e => updateLaneConfig(lane.name, 'endpoint', e.target.value)}
                      />
                    </div>

                    {/* Context Window */}
                    <div>
                      <label className="text-xs text-muted">Context Window</label>
                      <input 
                        className="input" type="number"
                        value={lane.config.context_window}
                        onChange={e => updateLaneConfig(lane.name, 'context_window', parseInt(e.target.value))}
                      />
                    </div>

                    {/* Quantization */}
                    <div>
                      <label className="text-xs text-muted">Quantization</label>
                      <select 
                        className="select"
                        value={lane.config.quantization}
                        onChange={e => updateLaneConfig(lane.name, 'quantization', e.target.value)}
                      >
                        {quantizations.map(q => (
                          <option key={q} value={q}>{q}</option>
                        ))}
                      </select>
                    </div>

                    {/* GPU Layers */}
                    <div>
                      <label className="text-xs text-muted">GPU Layers</label>
                      <input 
                        className="input" type="number"
                        value={lane.config.gpu_layers}
                        onChange={e => updateLaneConfig(lane.name, 'gpu_layers', parseInt(e.target.value))}
                      />
                    </div>

                    {/* Acceleration Mode */}
                    <div>
                      <label className="text-xs text-muted">Acceleration</label>
                      <select 
                        className="select"
                        value={lane.config.acceleration_mode}
                        onChange={e => updateLaneConfig(lane.name, 'acceleration_mode', e.target.value)}
                      >
                        {accelModes.map(m => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </select>
                    </div>

                    {/* Temperature */}
                    <div>
                      <label className="text-xs text-muted">Temperature</label>
                      <input 
                        type="range" min={0} max={2} step={0.1}
                        value={lane.config.temperature}
                        onChange={e => updateLaneConfig(lane.name, 'temperature', parseFloat(e.target.value))}
                      />
                      <span className="text-xs text-muted">{lane.config.temperature}</span>
                    </div>

                    {/* Max Tokens */}
                    <div>
                      <label className="text-xs text-muted">Max Tokens</label>
                      <input 
                        className="input" type="number"
                        value={lane.config.max_tokens}
                        onChange={e => updateLaneConfig(lane.name, 'max_tokens', parseInt(e.target.value))}
                      />
                    </div>

                    {/* Top P */}
                    <div>
                      <label className="text-xs text-muted">Top P</label>
                      <input 
                        type="range" min={0} max={1} step={0.05}
                        value={lane.config.top_p}
                        onChange={e => updateLaneConfig(lane.name, 'top_p', parseFloat(e.target.value))}
                      />
                      <span className="text-xs text-muted">{lane.config.top_p}</span>
                    </div>

                    {/* Top K */}
                    <div>
                      <label className="text-xs text-muted">Top K</label>
                      <input 
                        className="input" type="number"
                        value={lane.config.top_k}
                        onChange={e => updateLaneConfig(lane.name, 'top_k', parseInt(e.target.value))}
                      />
                    </div>

                    {/* Repeat Penalty */}
                    <div>
                      <label className="text-xs text-muted">Repeat Penalty</label>
                      <input 
                        className="input" type="number" step={0.1}
                        value={lane.config.repeat_penalty}
                        onChange={e => updateLaneConfig(lane.name, 'repeat_penalty', parseFloat(e.target.value))}
                      />
                    </div>
                  </div>

                  {/* Test buttons */}
                  <div className="flex gap-2 mt-4">
                    <button 
                      className="btn btn-primary text-xs"
                      onClick={() => activateLane(lane.name)}
                      disabled={config.active_lane === lane.name}
                    >
                      <Zap size={12} /> Set Active
                    </button>
                    <button 
                      className="btn btn-ghost text-xs"
                      onClick={() => testConnection(lane.name)}
                      disabled={testingLane === lane.name}
                    >
                      <Activity size={12} /> Test Connection
                    </button>
                    <button 
                      className="btn btn-ghost text-xs"
                      onClick={() => testResponse(lane.name)}
                      disabled={testingLane === lane.name}
                    >
                      <Play size={12} /> Test Response
                    </button>
                  </div>

                  {/* Test results */}
                  {testRes?.connection && (
                    <div className={`mt-3 p-3 rounded-md text-sm ${testRes.connection.passed ? 'text-success' : 'text-danger'}`} style={{ background: 'var(--color-surface-raised)' }}>
                      <div className="font-medium flex items-center gap-2">
                        {testRes.connection.passed ? <CheckCircle size={14} /> : <AlertTriangle size={14} />}
                        Connection: {testRes.connection.passed ? 'Passed' : 'Failed'}
                      </div>
                      <div className="text-xs text-muted mt-1">
                        TTF: {testRes.connection.ttf_ms}ms &bull; Total: {testRes.connection.latency_ms}ms
                      </div>
                    </div>
                  )}

                  {testRes?.response && (
                    <div className={`mt-3 p-3 rounded-md text-sm ${testRes.response.passed ? 'text-success' : 'text-danger'}`} style={{ background: 'var(--color-surface-raised)' }}>
                      <div className="font-medium flex items-center gap-2">
                        {testRes.response.passed ? <CheckCircle size={14} /> : <AlertTriangle size={14} />}
                        Response: {testRes.response.passed ? 'Passed' : 'Failed'}
                      </div>
                      <div className="text-xs text-muted mt-1">
                        TTF: {testRes.response.ttf_ms}ms &bull; Total: {testRes.response.latency_ms}ms
                      </div>
                      <div className="mt-2 p-2 rounded" style={{ background: 'var(--color-bg)', fontFamily: 'monospace', fontSize: 12 }}>
                        {testRes.response.sample_output}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Gateway status */}
      {gateway && (
        <div className="card mt-4">
          <div className="card-title mb-4">Gateway Status</div>
          <div className="flex items-center gap-2 text-sm">
            <Activity size={16} className="text-accent" />
            Routing: <strong>{gateway.routing_status}</strong>
            <span className="text-secondary">&bull; {gateway.lanes?.filter(l => l.healthy).length || 0}/{gateway.lanes?.length || 0} lanes healthy</span>
          </div>
        </div>
      )}
    </div>
  );
}
