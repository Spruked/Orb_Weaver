import { useState, useRef } from 'react'
import './App.css'

const PHIL_COLORS = {
  HUME:    '#3498db',
  KANT:    '#9b59b6',
  LOCKE:   '#e74c3c',
  SPINOZA: '#2ecc71',
}

function verdictClass(v) {
  if (!v) return 'verdict-error'
  const s = String(v).toLowerCase()
  if (s.includes('admit') || s.includes('grounded') || s.includes('respecting') || s.includes('true') || s.includes('imperative')) return 'verdict-admit'
  if (s.includes('reject') || s.includes('violation') || s.includes('impermissible')) return 'verdict-reject'
  return 'verdict-suspend'
}

function ConfBar({ value, color }) {
  const pct = Math.min(100, Math.round((value || 0) * 100))
  return (
    <div>
      <div className="conf-track">
        <div className="conf-fill" style={{ width: `${pct}%`, background: color || 'var(--cyan)' }} />
      </div>
    </div>
  )
}

function VerdictSection({ result }) {
  const contractViolated = result.synthesis?.contract_violated === true
  const violations = result.synthesis?.violations ?? result.invariants?.violations ?? []

  const rawConclusion = result.synthesis
    ? (result.synthesis.confidence > 0.6 ? 'admit' : result.synthesis.confidence < 0.3 ? 'reject' : 'suspend')
    : result.architectural_status?.includes('error') ? 'error' : 'suspend'

  // Contract breach forces downgrade — "admit" cannot stand when ECM failed
  const actualConclusion = contractViolated && rawConclusion === 'admit' ? 'suspend' : rawConclusion

  const conf = result.synthesis?.confidence ?? result.confidence ?? 0
  const vault = result.vault_status ?? '—'
  const latency = result.latency_ms ? `${result.latency_ms}ms` : '—'
  const coherenceStatus = result.phase_coherence?.status ?? '—'
  const escalated = result.escalation?.triggered

  return (
    <div className={`card ${contractViolated ? 'card-contract-violation' : ''}`}>
      <div className="card-title">Tribunal Verdict</div>
      <div className="verdict-row">
        <span className="verdict-label">Conclusion:</span>
        <span className={`verdict-value ${verdictClass(actualConclusion)}`}>
          {actualConclusion.toUpperCase()}
        </span>
      </div>
      <div className="verdict-row">
        <span className="verdict-label">Confidence:</span>
        <span className="verdict-value">{Math.round(conf * 100)}%</span>
      </div>
      <ConfBar value={conf} />
      <div className="verdict-row">
        <span className="verdict-label">Vault:</span>
        <span className="verdict-value">{vault}</span>
      </div>
      <div className="verdict-row">
        <span className="verdict-label">Latency:</span>
        <span className="verdict-value">{latency}</span>
      </div>
      <div className="verdict-row">
        <span className="verdict-label">Coherence:</span>
        <span className="verdict-value">{coherenceStatus}</span>
      </div>
      <div className="verdict-row">
        <span className="verdict-label">Escalated:</span>
        <span className="verdict-value">{escalated ? 'YES' : 'NO'}</span>
      </div>

      {violations.length > 0 && (
        <div className="violation-list">
          <div className="violation-label">Violations:</div>
          {violations.map((v, i) => (
            <span key={i} className="violation-item">{v}</span>
          ))}
        </div>
      )}
      {result.synthesis?.synthesis_trace?.length > 0 && (
        <details style={{ marginTop: 10 }}>
          <summary style={{ cursor: 'pointer', fontSize: 12, color: 'var(--cyan)' }}>
            Synthesis trace ({result.synthesis.synthesis_trace.length} steps)
          </summary>
          <pre className="trace-pre" style={{ marginTop: 6 }}>
            {result.synthesis.synthesis_trace.join('\n')}
          </pre>
        </details>
      )}
    </div>
  )
}

function PhilosopherSection({ result }) {
  const philResults = result.philosopher_results ?? {}
  const [expanded, setExpanded] = useState({})
  const toggle = name => setExpanded(e => ({ ...e, [name]: !e[name] }))

  const beams = Object.entries(philResults).map(([name, data]) => ({
    name,
    confidence: data.confidence ?? 0,
    verdict: data.verdict ?? '—',
    rationale_trace: data.rationale_trace ?? [],
    color: PHIL_COLORS[name] ?? 'var(--cyan)',
  }))

  if (!beams.length) return null

  return (
    <div className="card">
      <div className="card-title">Philosopher Beams</div>
      <div className="phil-grid">
        {beams.map(({ name, confidence, verdict, rationale_trace, color }) => (
          <div key={name} className="phil-row">
            <div
              className="phil-header"
              onClick={() => rationale_trace.length && toggle(name)}
              style={{ cursor: rationale_trace.length ? 'pointer' : 'default' }}
            >
              <span className="phil-name">{name}</span>
              <span className="phil-conf" style={{ color }}>{Math.round(confidence * 100)}%</span>
              {rationale_trace.length > 0 && (
                <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-dim)' }}>
                  {expanded[name] ? '▲' : '▼'}
                </span>
              )}
            </div>
            <ConfBar value={confidence} color={color} />
            <div className="phil-verdict">{verdict}</div>
            {expanded[name] && rationale_trace.length > 0 && (
              <pre className="trace-pre" style={{ marginTop: 6 }}>
                {rationale_trace.join('\n')}
              </pre>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function PipelineSection({ result }) {
  const coherenceScore = result.phase_coherence?.score ?? 0
  const driftIntact = result.drift_ping?.chain_intact
  const invPassed = result.invariants?.passed
  const vaultConf = typeof result.confidence === 'number' ? result.confidence : 0
  const escalation = result.escalation?.reason ?? 'none'
  const queries = result.query_id?.split('_')[1] ?? '—'

  function statusColor(val) {
    if (val === true) return 'var(--green)'
    if (val === false) return 'var(--red)'
    return 'var(--text-dim)'
  }

  return (
    <div className="card">
      <div className="card-title">Pipeline Status</div>
      <div className="pipe-grid">
        <div className="pipe-cell">
          <div className="pipe-cell-label">Phase Coherence</div>
          <div className="pipe-cell-value" style={{ color: coherenceScore > 0.6 ? 'var(--green)' : 'var(--gold)' }}>
            {Math.round(coherenceScore * 100)}%
          </div>
        </div>
        <div className="pipe-cell">
          <div className="pipe-cell-label">Drift Chain</div>
          <div className="pipe-cell-value" style={{ color: statusColor(driftIntact) }}>
            {driftIntact == null ? '—' : driftIntact ? 'OK' : 'WARN'}
          </div>
        </div>
        <div className="pipe-cell">
          <div className="pipe-cell-label">Invariants</div>
          <div className="pipe-cell-value" style={{ color: statusColor(invPassed) }}>
            {invPassed == null ? '—' : invPassed ? 'PASS' : 'FAIL'}
          </div>
        </div>
        <div className="pipe-cell">
          <div className="pipe-cell-label">Escalation</div>
          <div className="pipe-cell-value" style={{ fontSize: 12, color: escalation === 'none' ? 'var(--text-dim)' : 'var(--gold)' }}>
            {escalation}
          </div>
        </div>
        <div className="pipe-cell">
          <div className="pipe-cell-label">Query #</div>
          <div className="pipe-cell-value" style={{ color: 'var(--cyan)' }}>{queries}</div>
        </div>
        <div className="pipe-cell">
          <div className="pipe-cell-label">Vault Status</div>
          <div className="pipe-cell-value" style={{ fontSize: 12, color: result.vault_status === 'exact' ? 'var(--green)' : 'var(--gold)' }}>
            {result.vault_status ?? '—'}
          </div>
        </div>
        <div className="pipe-cell">
          <div className="pipe-cell-label">Drift Pings</div>
          <div className="pipe-cell-value" style={{ fontSize: 12, color: 'var(--cyan)', fontFamily: 'var(--mono)' }}>
            {result.drift_ping?.stats?.confirmed ?? '—'}/{result.drift_ping?.stats?.total_pings ?? '—'}
          </div>
        </div>
      </div>
    </div>
  )
}

function TestCard({ id, r }) {
  const [open, setOpen] = useState(false)
  const status = r?.status ?? 'ERROR'
  const confVal = r?.actual_confidence
  const hasConfNum = typeof confVal === 'number'
  const hasConfObj = confVal && typeof confVal === 'object'

  function confColor(v) {
    if (v >= 0.75) return 'var(--green)'
    if (v >= 0.45) return 'var(--gold)'
    return 'var(--red)'
  }

  return (
    <div className={`test-card ${status === 'PASS' ? 'test-card-pass' : status === 'FAIL' ? 'test-card-fail' : 'test-card-error'}`}>
      <div className="test-card-header" onClick={() => setOpen(o => !o)} style={{ cursor: 'pointer' }}>
        <span className={`test-badge ${status === 'PASS' ? 'pass' : 'fail'}`}>{status}</span>
        <span className="test-card-name">{r?.label ?? id.replace(/_/g, ' ')}</span>
        <span className="test-card-ms">{r?.elapsed_ms != null ? `${r.elapsed_ms}ms` : ''}</span>
        <span className="test-card-chevron">{open ? '▲' : '▼'}</span>
      </div>

      {open && (
        <div className="test-card-body">
          <div className="test-row">
            <span className="test-field">Beam</span>
            <span className="test-val">{r?.beam ?? '—'}</span>
          </div>
          <div className="test-row">
            <span className="test-field">Condition</span>
            <span className="test-val">{r?.condition ?? '—'}</span>
          </div>
          <div className="test-row">
            <span className="test-field">Expected</span>
            <span className="test-val">{r?.expected ?? '—'}</span>
          </div>
          <div className="test-row">
            <span className="test-field">Actual Confidence</span>
            <span className="test-val" style={{ color: hasConfNum ? confColor(confVal) : 'var(--text)' }}>
              {hasConfNum
                ? `${Math.round(confVal * 100)}%`
                : hasConfObj
                  ? Object.entries(confVal).map(([k, v]) => `${k}: ${Math.round(v * 100)}%`).join(' · ')
                  : String(confVal ?? '—')}
            </span>
          </div>
          {hasConfNum && (
            <ConfBar value={confVal} color={confColor(confVal)} />
          )}
          <div className="test-row">
            <span className="test-field">Conclusion</span>
            <span className="test-val" style={{ fontSize: 11, wordBreak: 'break-word' }}>
              {r?.actual_conclusion
                ? (typeof r.actual_conclusion === 'string'
                    ? r.actual_conclusion
                    : Object.entries(r.actual_conclusion).map(([k, v]) => `${k}: ${v}`).join(' · '))
                : '—'}
            </span>
          </div>
          {r?.dominant_rule && (
            <div className="test-row">
              <span className="test-field">Dominant Rule</span>
              <span className="test-val rule-tag">{r.dominant_rule}</span>
            </div>
          )}
          {r?.invariant_triggered && (
            <div className="test-row">
              <span className="test-field">Invariant Fired</span>
              <span className="test-val rule-tag" style={{ color: 'var(--gold)' }}>{r.invariant_triggered}</span>
            </div>
          )}
          {r?.phase_coherence && (
            <div className="test-row">
              <span className="test-field">Phase Coherence</span>
              <span className="test-val">{r.phase_coherence.score} · <em>{r.phase_coherence.status}</em></span>
            </div>
          )}
          {r?.why && (
            <div className="test-why">
              <div className="test-field">Why this verdict</div>
              <div className="test-why-text">{r.why}</div>
            </div>
          )}
          {r?.why_suspend && (
            <div className="test-why">
              <div className="test-field">Why suspend (not admit/reject)</div>
              <div className="test-why-text">{r.why_suspend}</div>
            </div>
          )}
          {r?.failed_alternatives && (
            <div className="test-why">
              <div className="test-field">Rejected alternatives</div>
              <ul style={{ margin: '4px 0 0 16px', padding: 0, fontSize: 12, color: 'var(--text-dim)' }}>
                {r.failed_alternatives.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            </div>
          )}
          {r?.beam_breakdown && (
            <div className="test-why">
              <div className="test-field">Beam breakdown (K²)</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 4 }}>
                {r.beam_breakdown.map((b, i) => (
                  <div key={i} className="beam-chip" style={{ borderColor: Object.values(PHIL_COLORS)[i % 4] }}>
                    <span style={{ color: Object.values(PHIL_COLORS)[i % 4], fontWeight: 700 }}>{b.name}</span>
                    <span style={{ marginLeft: 6, color: confColor(b.confidence) }}>{Math.round(b.confidence * 100)}%</span>
                    <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--text-dim)' }}>{b.conclusion}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {r?.trace && (
            <details className="test-trace">
              <summary style={{ cursor: 'pointer', fontSize: 12, color: 'var(--cyan)', marginTop: 8 }}>
                Rationale trace ({Array.isArray(r.trace) ? r.trace.length : Object.keys(r.trace).length} steps)
              </summary>
              <pre className="trace-pre">
                {Array.isArray(r.trace)
                  ? r.trace.join('\n')
                  : Object.entries(r.trace).map(([k, v]) => `[${k}]\n${Array.isArray(v) ? v.join('\n') : v}`).join('\n\n')}
              </pre>
            </details>
          )}
          {r?.error && (
            <div className="test-why" style={{ borderColor: 'var(--red)' }}>
              <div className="test-field" style={{ color: 'var(--red)' }}>Error</div>
              <div className="test-why-text" style={{ color: 'var(--red)' }}>{r.error}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function TestResultsSection({ results }) {
  if (results.error) {
    return (
      <div className="card error-card">
        <div className="card-title">Test Error</div>
        <div className="error-msg">{results.error}</div>
      </div>
    )
  }

  const entries = Object.entries(results)
  const passCount = entries.filter(([, r]) => r?.status === 'PASS').length
  const totalCount = entries.length
  const allPass = passCount === totalCount

  return (
    <div className="card">
      <div className="card-title">
        Hard Test Results
        <span style={{ marginLeft: 14, fontSize: 13, fontWeight: 400, color: allPass ? 'var(--green)' : 'var(--red)' }}>
          {passCount}/{totalCount} passed
        </span>
      </div>
      <div className="test-list">
        {entries.map(([id, r]) => (
          <TestCard key={id} id={id} r={r} />
        ))}
      </div>
    </div>
  )
}

// ── Beam disagreement: std-dev of the 4 beam confidences ─────────────────────
function beamDisagreement(result) {
  const pr = result?.philosopher_results
  if (!pr) return null
  const vals = Object.values(pr).map(v => v?.confidence ?? 0)
  if (!vals.length) return null
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length
  const variance = vals.reduce((a, b) => a + (b - mean) ** 2, 0) / vals.length
  return Math.sqrt(variance)
}

// ── Invariants that actually fired (violations list, or "none") ───────────────
function firedInvariants(result) {
  const v = result?.invariants?.violations ?? result?.synthesis?.violations ?? []
  return v.length ? v : null
}

function DiagnosticsPanel({ history, selectedIdx, onSelect }) {
  const [collapsed, setCollapsed] = useState(false)

  if (!history.length) return null

  const rows = history.map((item, i) => {
    const r = item.result ?? {}
    const conf = r.synthesis?.confidence ?? r.confidence ?? 0
    const rawVerdict = r.synthesis?.confidence > 0.6 ? 'admit'
      : r.synthesis?.confidence < 0.3 ? 'reject' : 'suspend'
    const verdict = (r.synthesis?.contract_violated && rawVerdict === 'admit') ? 'suspend' : rawVerdict
    const disagreement = beamDisagreement(r)
    const fired = firedInvariants(r)
    const escalation = r.escalation?.reason ?? 'none'
    const ms = r.latency_ms ?? null
    const traceId = r.query_id ?? '—'
    const isErr = !!r.error

    return { i, item, r, conf, verdict, disagreement, fired, escalation, ms, traceId, isErr }
  })

  const vCol = v => v === 'admit' ? 'var(--green)' : v === 'reject' ? 'var(--red)' : 'var(--gold)'
  const disCol = d => d == null ? 'var(--text-dim)' : d > 0.25 ? 'var(--red)' : d > 0.1 ? 'var(--gold)' : 'var(--green)'

  return (
    <div className="card diag-card">
      <div className="diag-header" onClick={() => setCollapsed(c => !c)} style={{ cursor: 'pointer' }}>
        <span className="card-title" style={{ margin: 0 }}>Query Diagnostics Log</span>
        <span style={{ fontSize: 12, color: 'var(--text-dim)', marginLeft: 10 }}>
          {history.length} {history.length === 1 ? 'query' : 'queries'}
        </span>
        <span style={{ marginLeft: 'auto', fontSize: 13, color: 'var(--cyan)' }}>
          {collapsed ? '▼' : '▲'}
        </span>
      </div>

      {!collapsed && (
        <div className="diag-table-wrap">
          <table className="diag-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Query</th>
                <th>Verdict</th>
                <th>Conf</th>
                <th>Beam Δ</th>
                <th>Invariant Fired</th>
                <th>Escalation</th>
                <th>ms</th>
                <th>Trace ID</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ i, item, r, conf, verdict, disagreement, fired, escalation, ms, traceId, isErr }) => (
                <tr
                  key={i}
                  className={`diag-row ${selectedIdx === i ? 'diag-row-active' : ''}`}
                  onClick={() => onSelect(i)}
                >
                  <td className="diag-num">{history.length - i}</td>

                  <td className="diag-query">
                    <span className="diag-query-text">{item.text}</span>
                  </td>

                  <td>
                    {isErr
                      ? <span className="diag-chip" style={{ color: 'var(--red)', borderColor: 'var(--red)' }}>ERROR</span>
                      : <span className="diag-chip" style={{ color: vCol(verdict), borderColor: vCol(verdict) }}>
                          {verdict.toUpperCase()}
                        </span>
                    }
                  </td>

                  <td>
                    <div className="diag-conf-wrap">
                      <span style={{ color: vCol(verdict), fontWeight: 700, fontSize: 12 }}>
                        {isErr ? '—' : `${Math.round(conf * 100)}%`}
                      </span>
                      {!isErr && (
                        <div className="diag-conf-track">
                          <div className="diag-conf-fill"
                            style={{ width: `${Math.round(conf * 100)}%`, background: vCol(verdict) }} />
                        </div>
                      )}
                    </div>
                  </td>

                  <td>
                    {disagreement == null
                      ? <span style={{ color: 'var(--text-dim)' }}>—</span>
                      : <span style={{ color: disCol(disagreement), fontWeight: 700, fontSize: 12 }}>
                          {(disagreement * 100).toFixed(1)}%
                          <span style={{ fontSize: 10, color: 'var(--text-dim)', marginLeft: 4 }}>
                            {disagreement > 0.25 ? 'high' : disagreement > 0.1 ? 'med' : 'low'}
                          </span>
                        </span>
                    }
                  </td>

                  <td className="diag-inv">
                    {fired
                      ? fired.map((f, fi) => (
                          <span key={fi} className="diag-inv-tag">{f}</span>
                        ))
                      : <span className="diag-inv-ok">✓ none</span>
                    }
                  </td>

                  <td>
                    <span style={{
                      fontSize: 11,
                      color: escalation === 'none' || !escalation ? 'var(--text-dim)' : 'var(--gold)',
                      fontStyle: escalation === 'none' ? 'italic' : 'normal',
                    }}>
                      {escalation || 'none'}
                    </span>
                  </td>

                  <td>
                    <span style={{ fontSize: 11, color: 'var(--cyan)', fontFamily: 'var(--mono)' }}>
                      {ms != null ? ms : '—'}
                    </span>
                  </td>

                  <td className="diag-trace-id">
                    <span title={traceId}>{traceId.replace('query_', 'q').split('_').slice(0,2).join('_')}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function HistoryItem({ item, active, onClick }) {
  const conf = item.result?.confidence ?? 0
  const verdict = item.result?.synthesis?.confidence > 0.6 ? 'admit'
    : item.result?.synthesis?.confidence < 0.3 ? 'reject' : 'suspend'
  const color = verdict === 'admit' ? 'var(--green)' : verdict === 'reject' ? 'var(--red)' : 'var(--gold)'

  return (
    <div className={`history-item ${active ? 'active' : ''}`} onClick={onClick}>
      <div className="history-text">{item.text}</div>
      <div className="history-meta">
        <span style={{ fontSize: 10, fontWeight: 700, color, textTransform: 'uppercase' }}>{verdict}</span>
        <span style={{ fontSize: 10, color: 'var(--text-dim)', marginLeft: 'auto' }}>
          {Math.round(conf * 100)}%
        </span>
      </div>
    </div>
  )
}

export default function App() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])
  const [selected, setSelected] = useState(null)
  const [testResults, setTestResults] = useState(null)
  const [runningTests, setRunningTests] = useState(false)
  const [recording, setRecording] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const textRef = useRef()
  const mediaRef = useRef(null)
  const chunksRef = useRef([])

  const selectedResult = selected !== null ? history[selected]?.result : null

  async function submit() {
    if (!text.trim() || loading) return
    setLoading(true)
    try {
      const res = await fetch('/api/reason', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim() }),
      })
      const data = await res.json()
      const entry = { text: text.trim(), result: data }
      setHistory(h => [entry, ...h])
      setSelected(0)
      setText('')
    } catch (e) {
      const entry = { text: text.trim(), result: { error: e.message, architectural_status: 'error' } }
      setHistory(h => [entry, ...h])
      setSelected(0)
    } finally {
      setLoading(false)
    }
  }

  async function runTests() {
    setRunningTests(true)
    try {
      const res = await fetch('/api/run-tests')
      const data = await res.json()
      setTestResults(data.test_results)
      setSelected(null)
    } catch (e) {
      setTestResults({ error: e.message })
    } finally {
      setRunningTests(false)
    }
  }

  async function toggleRecord() {
    if (recording) {
      mediaRef.current?.stop()
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      chunksRef.current = []
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      mediaRef.current = mr
      mr.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        setRecording(false)
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        await submitAudio(blob)
      }
      mr.start()
      setRecording(true)
    } catch (err) {
      alert(`Microphone error: ${err.message}`)
    }
  }

  async function submitAudio(blob) {
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('file', blob, 'recording.webm')
      const res = await fetch('/api/reason-audio', { method: 'POST', body: fd })
      const data = await res.json()
      const transcriptText = data.transcript ?? '(no transcript)'
      const entry = { text: `🎙 ${transcriptText}`, result: data }
      setHistory(h => [entry, ...h])
      setSelected(0)
      setTestResults(null)
    } catch (e) {
      const entry = { text: '🎙 (audio error)', result: { error: e.message, architectural_status: 'error' } }
      setHistory(h => [entry, ...h])
      setSelected(0)
    } finally {
      setLoading(false)
    }
  }

  async function speakVerdict() {
    if (!selectedResult?.synthesis?.final_conclusion) return
    const conf = selectedResult.synthesis?.confidence ?? 0
    const verdict = conf > 0.6 ? 'admit' : conf < 0.3 ? 'reject' : 'suspend'
    const tts = `Tribunal verdict: ${verdict}. Confidence: ${Math.round(conf * 100)} percent. ${selectedResult.synthesis?.final_conclusion ?? ''}`
    setSpeaking(true)
    try {
      const res = await fetch('/api/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: tts }),
      })
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail ?? 'TTS error') }
      const audioBlob = await res.blob()
      const url = URL.createObjectURL(audioBlob)
      const audio = new Audio(url)
      audio.onended = () => { URL.revokeObjectURL(url); setSpeaking(false) }
      await audio.play()
    } catch (err) {
      setSpeaking(false)
      alert(`TTS: ${err.message}`)
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submit()
  }

  const adjustedSelected = selected !== null && history.length > 0
    ? Math.min(selected, history.length - 1)
    : null

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-dot" />
        <span className="header-title">Triple Predicate Cubed</span>
        <span className="header-sub">18D · 4 Beams · 30 Invariants · 0.95 cap</span>
      </header>

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="query-panel">
          <textarea
            ref={textRef}
            rows={5}
            placeholder="Enter input text… (Ctrl+Enter to run)"
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={handleKey}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="submit-btn" onClick={submit} disabled={loading || !text.trim()} style={{ flex: 1 }}>
              {loading ? 'PROCESSING…' : 'RUN TPC'}
            </button>
            <button
              className={`mic-btn ${recording ? 'mic-active' : ''}`}
              onClick={toggleRecord}
              disabled={loading}
              title={recording ? 'Stop recording' : 'Record audio query'}
            >
              {recording ? '⏹' : '🎙'}
            </button>
          </div>
          <button className="submit-btn" onClick={runTests} disabled={runningTests} style={{ marginTop: 4 }}>
            {runningTests ? 'RUNNING TESTS…' : 'RUN HARD TESTS'}
          </button>
          {selectedResult && !selectedResult.error && (
            <button
              className="submit-btn"
              onClick={speakVerdict}
              disabled={speaking}
              style={{ marginTop: 4, background: 'var(--gold)', color: '#000' }}
            >
              {speaking ? '🔊 SPEAKING…' : '🔊 SPEAK VERDICT'}
            </button>
          )}
        </div>

        <div className="history-panel">
          {history.length > 0 && <div className="history-label">History</div>}
          {history.map((item, i) => (
            <HistoryItem
              key={i}
              item={item}
              active={adjustedSelected === i}
              onClick={() => { setSelected(i); setTestResults(null) }}
            />
          ))}
        </div>
      </aside>

      {/* Main */}
      <main className="main">
        {testResults ? (
          <TestResultsSection results={testResults} />
        ) : !selectedResult ? (
          <div className="empty-state">
            <div className="empty-glyph">⬡</div>
            <div>Enter text and press RUN TPC</div>
            <div style={{ fontSize: 12 }}>Ctrl+Enter to submit · 🎙 for voice</div>
          </div>
        ) : selectedResult.error ? (
          <div className={`card error-card`}>
            <div className="card-title">Pipeline Error</div>
            <div className="error-msg">{selectedResult.error}</div>
          </div>
        ) : (
          <>
            <VerdictSection result={selectedResult} />
            {selectedResult.cochlear && (
              <div className="card">
                <div className="card-title">Cochlear 3.0 Report</div>
                {selectedResult.cochlear.available === false ? (
                  <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>
                    Cochlear processor unavailable: {selectedResult.cochlear.error}
                  </div>
                ) : (
                  <>
                    <div className="verdict-row" style={{ marginBottom: 6 }}>
                      <span className="verdict-label">Raw transcript</span>
                      <span className="verdict-value" style={{ fontSize: 12, fontFamily: 'var(--mono)' }}>
                        {selectedResult.cochlear.raw_transcript}
                      </span>
                    </div>
                    <div className="verdict-row" style={{ marginBottom: 6 }}>
                      <span className="verdict-label">Corrected</span>
                      <span className="verdict-value" style={{ fontSize: 12, color: 'var(--green)', fontFamily: 'var(--mono)' }}>
                        {selectedResult.cochlear.corrected_transcript}
                      </span>
                    </div>
                    <div className="verdict-row">
                      <span className="verdict-label">Corrections</span>
                      <span className="verdict-value">{selectedResult.cochlear.corrections_made}</span>
                    </div>
                    <div className="verdict-row">
                      <span className="verdict-label">Perceptual conf</span>
                      <span className="verdict-value">
                        {Math.round((selectedResult.cochlear.perceptual_confidence ?? 0) * 100)}%
                      </span>
                    </div>
                    <ConfBar value={selectedResult.cochlear.perceptual_confidence ?? 0} color="var(--cyan)" />
                  </>
                )}
              </div>
            )}
            <PhilosopherSection result={selectedResult} />
            <PipelineSection result={selectedResult} />
          </>
        )}
        <DiagnosticsPanel
          history={history}
          selectedIdx={adjustedSelected}
          onSelect={i => { setSelected(i); setTestResults(null) }}
        />
      </main>
    </div>
  )
}
