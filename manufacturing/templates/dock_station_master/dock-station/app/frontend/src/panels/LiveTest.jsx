import React, { useState, useEffect, useRef, useCallback } from 'react';
import { liveTest, profiles } from '../services/api';
import { 
  Play, Square, Mic, MicOff, Volume2, VolumeX, RotateCcw, 
  Smartphone, Globe, Crosshair, Activity, Zap, Shield, 
  MessageSquare, Clock, Cpu, Target, ChevronDown, ChevronUp,
  Send, Radio
} from 'lucide-react';

export default function LiveTest({ profileId }) {
  const [session, setSession] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [status, setStatus] = useState('idle');
  const [inputText, setInputText] = useState('');
  const [url, setUrl] = useState('http://localhost:3000');
  const [route, setRoute] = useState('/');
  const [mobileSim, setMobileSim] = useState(false);
  const [muted, setMuted] = useState(false);
  const [micAllowed, setMicAllowed] = useState(false);
  const [showMetrics, setShowMetrics] = useState(true);
  const [profile, setProfile] = useState(null);
  const transcriptRef = useRef(null);
  const pollRef = useRef(null);

  useEffect(() => {
    if (profileId) {
      profiles.get(profileId).then(setProfile);
    }
  }, [profileId]);

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [session?.transcript]);

  const pollSession = useCallback(async (sid) => {
    try {
      const data = await liveTest.getSession(sid);
      setSession(data);
      setStatus(data.status);
      setMuted(data.muted);
      setMobileSim(data.mobile_simulation);
    } catch (e) {
      console.error('Poll failed', e);
    }
  }, []);

  const startSession = async () => {
    if (!profileId) return;
    const data = await liveTest.start(profileId);
    setSessionId(data.session_id);
    setSession(data);
    setStatus(data.status);
    setMicAllowed(data.microphone_allowed);

    // Start polling
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(() => pollSession(data.session_id), 1000);
  };

  const stopSession = async () => {
    if (!sessionId) return;
    await liveTest.control(sessionId, 'stop');
    if (pollRef.current) clearInterval(pollRef.current);
    setStatus('idle');
    setSession(null);
    setSessionId(null);
  };

  const resetSession = async () => {
    if (!sessionId) return;
    const data = await liveTest.control(sessionId, 'reset');
    setSession(data);
    setStatus(data.status);
  };

  const toggleMute = async () => {
    if (!sessionId) return;
    const action = muted ? 'unmute' : 'mute';
    const data = await liveTest.control(sessionId, action);
    setSession(data);
    setMuted(data.muted);
  };

  const toggleMobile = async () => {
    if (!sessionId) return;
    setMobileSim(!mobileSim);
  };

  const reloadSiteWorld = async () => {
    if (!sessionId) return;
    const data = await liveTest.control(sessionId, 'reload_site_world');
    setSession(data);
  };

  const changeRoute = async () => {
    if (!sessionId) return;
    const data = await liveTest.control(sessionId, 'set_route', { route });
    setSession(data);
  };

  const sendVisitorMessage = async () => {
    if (!sessionId || !inputText.trim()) return;
    const data = await liveTest.speak(sessionId, inputText);
    setSession(data);
    setInputText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendVisitorMessage();
    }
  };

  // Orb visual state based on session
  const orbState = session?.status || 'idle';
  const orbColor = {
    idle: '#7c3aed',
    listening: '#22c55e',
    thinking: '#f59e0b',
    speaking: '#3b82f6',
    error: '#ef4444',
  }[orbState] || '#7c3aed';

  const orbGlow = {
    idle: '0 0 20px rgba(124,58,237,0.3)',
    listening: '0 0 30px rgba(34,197,94,0.5)',
    thinking: '0 0 30px rgba(245,158,11,0.5)',
    speaking: '0 0 30px rgba(59,130,246,0.5)',
    error: '0 0 30px rgba(239,68,68,0.5)',
  }[orbState] || 'none';

  if (!profileId) {
    return (
      <div className="p-6 text-secondary" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
        <div className="text-center">
          <Radio size={48} className="text-muted mb-4" />
          <p>Select a profile from Overview to start Live Test.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6" style={{ maxWidth: 1400, height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Live Test</h1>
          <p className="text-secondary">Draft testing environment — no effect on published ORB</p>
        </div>
        <div className="flex gap-2">
          {!sessionId ? (
            <button className="btn btn-success" onClick={startSession}>
              <Play size={14} /> Start Session
            </button>
          ) : (
            <>
              <button className="btn btn-danger" onClick={stopSession}>
                <Square size={14} /> Stop
              </button>
              <button className="btn btn-ghost" onClick={toggleMute}>
                {muted ? <VolumeX size={14} /> : <Volume2 size={14} />}
                {muted ? ' Unmute' : ' Mute'}
              </button>
              <button className="btn btn-ghost" onClick={resetSession}>
                <RotateCcw size={14} /> Reset
              </button>
              <button className={`btn ${mobileSim ? 'btn-primary' : 'btn-ghost'}`} onClick={toggleMobile}>
                <Smartphone size={14} /> Mobile
              </button>
            </>
          )}
        </div>
      </div>

      {/* URL / Route bar */}
      <div className="card mb-4" style={{ padding: 12 }}>
        <div className="flex gap-3 items-center">
          <Globe size={16} className="text-muted" />
          <input 
            className="input" 
            style={{ maxWidth: 300 }}
            value={url} 
            onChange={e => setUrl(e.target.value)}
            placeholder="Website URL"
          />
          <span className="text-muted">Route:</span>
          <input 
            className="input" 
            style={{ maxWidth: 150 }}
            value={route} 
            onChange={e => setRoute(e.target.value)}
            placeholder="/"
          />
          <button className="btn btn-ghost text-xs" onClick={changeRoute} disabled={!sessionId}>
            Set Route
          </button>
          <button className="btn btn-ghost text-xs" onClick={reloadSiteWorld} disabled={!sessionId}>
            <RotateCcw size={12} /> Reload Site World
          </button>
          <div style={{ marginLeft: 'auto' }} className="flex items-center gap-2">
            <span className={`badge badge-${status === 'listening' ? 'healthy' : status === 'thinking' ? 'warning' : status === 'speaking' ? 'published' : 'draft'}`}>
              {status}
            </span>
            {session?.draft_testing !== false && (
              <span className="badge badge-warning">DRAFT</span>
            )}
          </div>
        </div>
      </div>

      {/* Main content */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 16, flex: 1, minHeight: 0 }}>
        {/* Left: Website viewport + ORB overlay */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden', position: 'relative' }}>
          {/* Simulated website viewport */}
          <div style={{ 
            flex: 1, 
            background: 'var(--color-surface-raised)', 
            position: 'relative',
            overflow: 'hidden',
            borderRadius: 'var(--radius-md)',
          }}>
            {/* Mock website content */}
            <div style={{ 
              padding: 40, 
              opacity: 0.3,
              pointerEvents: 'none',
              filter: mobileSim ? 'blur(0px)' : 'none',
            }}>
              <div style={{ height: 60, background: 'var(--color-border)', borderRadius: 8, marginBottom: 24 }} />
              <div style={{ height: 200, background: 'var(--color-border)', borderRadius: 8, marginBottom: 16 }} />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
                <div style={{ height: 120, background: 'var(--color-border)', borderRadius: 8 }} />
                <div style={{ height: 120, background: 'var(--color-border)', borderRadius: 8 }} />
                <div style={{ height: 120, background: 'var(--color-border)', borderRadius: 8 }} />
              </div>
            </div>

            {/* ORB overlay */}
            {sessionId && (
              <div style={{
                position: 'absolute',
                bottom: 40,
                right: 40,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 12,
              }}>
                {/* ORB sphere */}
                <div style={{
                  width: 80,
                  height: 80,
                  borderRadius: '50%',
                  background: `radial-gradient(circle at 30% 30%, ${orbColor}, ${orbColor}88)`,
                  boxShadow: orbGlow,
                  transition: 'all 0.5s ease',
                  animation: orbState === 'listening' ? 'pulse 1.5s infinite' : orbState === 'thinking' ? 'spin 2s linear infinite' : 'none',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  {orbState === 'listening' && <Mic size={28} color="white" />}
                  {orbState === 'thinking' && <Activity size={28} color="white" />}
                  {orbState === 'speaking' && <Volume2 size={28} color="white" />}
                  {orbState === 'idle' && <Zap size={28} color="white" />}
                </div>
                <div className="text-xs text-muted" style={{ textTransform: 'capitalize' }}>{orbState}</div>
              </div>
            )}

            {/* Pointer target indicator */}
            {session?.pointer_target && (
              <div style={{
                position: 'absolute',
                left: session.pointer_target.x,
                top: session.pointer_target.y,
                width: 40,
                height: 40,
                borderRadius: '50%',
                border: '2px solid var(--color-accent)',
                background: 'rgba(124,58,237,0.2)',
                animation: 'pulse 1s infinite',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <Crosshair size={16} color="var(--color-accent-light)" />
              </div>
            )}
          </div>

          {/* Input bar */}
          {sessionId && (
            <div style={{ padding: 12, borderTop: '1px solid var(--color-border-subtle)', display: 'flex', gap: 8 }}>
              <button 
                className="btn btn-ghost" 
                style={{ padding: '8px 10px' }}
                onClick={() => setMicAllowed(!micAllowed)}
              >
                {micAllowed ? <Mic size={16} className="text-success" /> : <MicOff size={16} className="text-danger" />}
              </button>
              <input 
                className="input"
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={micAllowed ? "Speak or type a message..." : "Type a message to simulate visitor input..."}
              />
              <button className="btn btn-primary" onClick={sendVisitorMessage} disabled={!inputText.trim()}>
                <Send size={14} />
              </button>
            </div>
          )}
        </div>

        {/* Right: Metrics + Transcript */}
        <div className="flex flex-col gap-3" style={{ overflow: 'hidden' }}>
          {/* Metrics panel */}
          <div className="card" style={{ padding: 12 }}>
            <div 
              className="flex justify-between items-center cursor-pointer"
              onClick={() => setShowMetrics(!showMetrics)}
            >
              <div className="card-title" style={{ fontSize: 13, marginBottom: 0 }}>Live Metrics</div>
              {showMetrics ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </div>

            {showMetrics && (
              <div className="flex flex-col gap-2 mt-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted">Stage</span>
                  <span className="font-medium">{session?.current_stage || '—'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted">Intent</span>
                  <span className="font-medium">{session?.detected_intent || '—'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted">Confidence</span>
                  <span className="font-medium text-accent">{session?.confidence ? `${Math.round(session.confidence * 100)}%` : '—'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted">Latency</span>
                  <span className="font-medium">{session?.latency_ms ? `${session.latency_ms}ms` : '—'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted">Active Lane</span>
                  <span className="font-medium">{session?.active_lane || '—'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted">Pointer</span>
                  <span className="font-medium">{session?.pointer_target?.id || '—'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted">Mic</span>
                  <span className={session?.microphone_allowed ? 'text-success' : 'text-muted'}>
                    {session?.microphone_allowed ? 'Allowed' : 'Blocked'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted">Speaker</span>
                  <span className={session?.speaker_active ? 'text-success' : 'text-muted'}>
                    {session?.speaker_active ? 'Active' : 'Off'}
                  </span>
                </div>

                {/* Allowed actions */}
                <div style={{ marginTop: 4 }}>
                  <div className="text-xs text-muted mb-1">ALLOWED ACTIONS</div>
                  <div className="flex flex-wrap gap-1">
                    {(session?.allowed_actions || []).map(action => (
                      <span key={action} className="badge" style={{ background: 'var(--color-surface-raised)', fontSize: 10 }}>
                        {action}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Tool calls */}
                {session?.tool_calls?.length > 0 && (
                  <div style={{ marginTop: 4 }}>
                    <div className="text-xs text-muted mb-1">TOOL CALLS</div>
                    {session.tool_calls.map((tc, i) => (
                      <div key={i} className="flex justify-between text-xs p-1 rounded" style={{ background: 'var(--color-surface-raised)' }}>
                        <span>{tc.tool}</span>
                        <span className={tc.requires_confirmation ? 'text-warning' : 'text-success'}>
                          {tc.status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Transcript */}
          <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 12, minHeight: 0 }}>
            <div className="card-title" style={{ fontSize: 13, marginBottom: 8 }}>Transcript</div>
            <div 
              ref={transcriptRef}
              style={{ 
                flex: 1, 
                overflow: 'auto', 
                display: 'flex', 
                flexDirection: 'column', 
                gap: 8,
                paddingRight: 4,
              }}
            >
              {!session?.transcript?.length && (
                <div className="text-muted text-sm text-center" style={{ marginTop: 40 }}>
                  Start a session to see the transcript.
                </div>
              )}
              {session?.transcript?.map((turn, i) => (
                <div 
                  key={i} 
                  className={`flex ${turn.speaker === 'weaver' ? 'justify-start' : 'justify-end'}`}
                >
                  <div 
                    style={{ 
                      maxWidth: '90%',
                      padding: '8px 12px',
                      borderRadius: turn.speaker === 'weaver' ? '4px 12px 12px 12px' : '12px 4px 12px 12px',
                      background: turn.speaker === 'weaver' ? 'var(--color-surface-raised)' : 'var(--color-accent)',
                      color: turn.speaker === 'weaver' ? 'var(--color-text)' : 'white',
                      fontSize: 13,
                    }}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs opacity-70" style={{ textTransform: 'capitalize', fontWeight: 500 }}>
                        {turn.speaker}
                      </span>
                      {turn.latency_ms && (
                        <span className="text-xs opacity-50">{turn.latency_ms}ms</span>
                      )}
                    </div>
                    <div>{turn.text}</div>
                    {turn.intent && (
                      <div className="text-xs opacity-70 mt-1">
                        Intent: {turn.intent} ({Math.round(turn.confidence * 100)}%)
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
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
