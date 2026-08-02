import React, { useState, useEffect } from 'react';
import { speech } from '../services/api';
import { Play, AlertCircle, CheckCircle } from 'lucide-react';

export default function SpeechListening({ profileId }) {
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    if (profileId) load();
  }, [profileId]);

  async function load() {
    const data = await speech.get(profileId);
    setSettings(data);
  }

  async function save(patch) {
    setSaving(true);
    const updated = { ...settings, ...patch };
    await speech.update(profileId, updated);
    setSettings(updated);
    setSaving(false);
  }

  async function testGreeting() {
    const res = await speech.testGreeting(profileId);
    setTestResult(res);
  }

  async function testTone() {
    const res = await speech.testTone(profileId);
    setTestResult(res);
  }

  if (!settings) return <div className="p-6 text-secondary">Select a profile to configure speech settings.</div>;

  return (
    <div className="p-6" style={{ maxWidth: 900 }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Speech & Listening</h1>
      <p className="text-secondary mb-6">Configure how Weaver listens, interrupts, and speaks.</p>

      <div className="flex flex-col gap-4">
        <div className="card">
          <div className="card-title mb-4">Greeting</div>
          <textarea 
            className="textarea" 
            rows={3}
            value={settings.greeting_text}
            onChange={e => save({ greeting_text: e.target.value })}
          />
          <div className="flex gap-2 mt-3">
            <button className="btn btn-primary" onClick={testGreeting}>
              <Play size={14} /> Test Greeting
            </button>
            <button className="btn btn-ghost" onClick={testTone}>
              <AlertCircle size={14} /> Tone Check
            </button>
          </div>
          {testResult && (
            <div className={`mt-3 p-3 rounded-md ${testResult.passed ? 'text-success' : 'text-warning'}`} style={{ background: 'var(--color-surface-raised)' }}>
              <div className="flex items-center gap-2 font-medium">
                {testResult.passed ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
                {testResult.test_type === 'greeting' ? 'Greeting test' : 'Tone check'}: {testResult.passed ? 'Passed' : 'Flagged'}
              </div>
              <div className="text-sm mt-1">{testResult.notes}</div>
              {testResult.tone_flags?.length > 0 && (
                <div className="text-xs mt-2 text-warning">Flags: {testResult.tone_flags.join(', ')}</div>
              )}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">Interruption</div>
            <div 
              className={`toggle ${settings.allow_interruption ? 'active' : ''}`}
              onClick={() => save({ allow_interruption: !settings.allow_interruption })}
            />
          </div>
          {settings.allow_interruption && (
            <div className="mt-3">
              <label className="text-xs text-muted">Sensitivity</label>
              <input 
                type="range" min={0} max={1} step={0.1}
                value={settings.interruption_sensitivity}
                onChange={e => save({ interruption_sensitivity: parseFloat(e.target.value) })}
              />
              <div className="flex justify-between text-xs text-muted mt-1">
                <span>Low</span>
                <span>{settings.interruption_sensitivity}</span>
                <span>High</span>
              </div>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title mb-4">Timing</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <label className="text-xs text-muted">Pause timeout (ms)</label>
              <input 
                className="input" type="number"
                value={settings.pause_timeout_ms}
                onChange={e => save({ pause_timeout_ms: parseInt(e.target.value) })}
              />
            </div>
            <div>
              <label className="text-xs text-muted">Prefix padding (ms)</label>
              <input 
                className="input" type="number"
                value={settings.prefix_padding_ms}
                onChange={e => save({ prefix_padding_ms: parseInt(e.target.value) })}
              />
            </div>
            <div>
              <label className="text-xs text-muted">Microphone sensitivity</label>
              <input 
                type="range" min={0} max={1} step={0.1}
                value={settings.microphone_sensitivity}
                onChange={e => save({ microphone_sensitivity: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <label className="text-xs text-muted">Re-engage delay (ms)</label>
              <input 
                className="input" type="number"
                value={settings.reengage_delay_ms}
                onChange={e => save({ reengage_delay_ms: parseInt(e.target.value) })}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
