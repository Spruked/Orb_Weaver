import { useState, useEffect, useCallback } from 'react'
import { useTPCStore } from '@stores/tpcStore'
import { PipelineStage } from './PipelineStage'
import { InputPanel } from './InputPanel'
import { OutputPanel } from './OutputPanel'

export function PipelineDashboard() {
  const [input, setInput] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const { 
    result, 
    setResult, 
    addToHistory,
    wsConnected,
    connect,
    disconnect 
  } = useTPCStore()

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  const handleSubmit = useCallback(async () => {
    if (!input.trim() || isProcessing) return

    setIsProcessing(true)

    try {
      const response = await fetch('/api/v1/reason', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          input: input,
          input_type: 'text',
          session_id: `session_${Date.now()}`
        })
      })

      const data = await response.json()
      setResult(data)
      addToHistory(data)
    } catch (error) {
      console.error('Pipeline error:', error)
    } finally {
      setIsProcessing(false)
    }
  }, [input, isProcessing, setResult, addToHistory])

  const stages = [
    { id: 'acp', name: 'ACP', desc: 'Cochlear Synthesis', active: isProcessing },
    { id: 'hlsf', name: 'HLSF', desc: '18D Traversal', active: isProcessing },
    { id: 'k0', name: 'K0', desc: 'Surface Reasoning', active: isProcessing },
    { id: 'k1', name: 'K1', desc: 'Abstract Reasoning', active: isProcessing },
    { id: 'k2', name: 'K2', desc: 'Deep Reasoning', active: isProcessing },
    { id: 'beams', name: '4-Beam', desc: 'Philosopher Loops', active: isProcessing },
    { id: 'coherence', name: 'Phase', desc: 'Coherence Check', active: isProcessing },
    { id: 'egf', name: 'EGF', desc: 'Certainty Gravity', active: isProcessing },
    { id: 'vault', name: 'Vault', desc: 'Glyph Retrieval', active: isProcessing },
    { id: 'ecm', name: 'ECM', desc: 'Epistemic Contract', active: isProcessing },
  ]

  return (
    <div className="h-full flex flex-col p-6 gap-4 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-orb-text">TPC Pipeline</h1>
          <p className="text-sm text-orb-text-dim">
            Triple Predicate Cubed — Full Reasoning Flow
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-orb-success' : 'bg-orb-error'}`} />
          <span className="text-xs text-orb-text-dim">
            {wsConnected ? 'WebSocket Connected' : 'WebSocket Disconnected'}
          </span>
        </div>
      </div>

      {/* Main Grid */}
      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
        {/* Left: Input + Stages */}
        <div className="col-span-7 flex flex-col gap-4">
          <InputPanel 
            value={input} 
            onChange={setInput} 
            onSubmit={handleSubmit}
            isProcessing={isProcessing}
          />

          {/* Pipeline Stages */}
          <div className="bg-orb-panel rounded-lg border border-orb-border p-4">
            <h3 className="text-sm font-semibold text-orb-text mb-3">Pipeline Stages</h3>
            <div className="grid grid-cols-5 gap-2">
              {stages.map((stage) => (
                <PipelineStage
                  key={stage.id}
                  name={stage.name}
                  desc={stage.desc}
                  active={stage.active}
                  completed={result && !stage.active}
                />
              ))}
            </div>
          </div>

          {/* Depth Visualization */}
          {result && (
            <DepthVisualizer 
              depthTrace={result.depth_trace || []}
            />
          )}
        </div>

        {/* Right: Output + Metrics */}
        <div className="col-span-5 flex flex-col gap-4">
          <OutputPanel result={result} />

          {result && (
            <>
              <CoherenceGauge 
                score={result.coherence?.score || 0}
                status={result.coherence?.status || 'unknown'}
              />

              {/* Philosopher Verdicts */}
              <div className="bg-orb-panel rounded-lg border border-orb-border p-4">
                <h3 className="text-sm font-semibold text-orb-text mb-3">Philosopher Verdicts</h3>
                <div className="space-y-2">
                  {result.philosopher_verdicts && Object.entries(result.philosopher_verdicts).map(([name, verdict]) => (
                    <div key={name} className="flex items-center justify-between">
                      <span className={`text-sm font-medium ${
                        name === 'Hume' ? 'text-orb-hume' :
                        name === 'Kant' ? 'text-orb-kant' :
                        name === 'Locke' ? 'text-orb-locke' :
                        'text-orb-spinoza'
                      }`}>
                        {name}
                      </span>
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-2 bg-orb-bg rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${
                              verdict.confidence > 0.7 ? 'bg-orb-success' :
                              verdict.confidence > 0.4 ? 'bg-orb-warning' :
                              'bg-orb-error'
                            }`}
                            style={{ width: `${verdict.confidence * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-orb-text-dim w-12 text-right">
                          {(verdict.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Drift Report */}
              <div className="bg-orb-panel rounded-lg border border-orb-border p-4">
                <h3 className="text-sm font-semibold text-orb-text mb-2">Drift Report</h3>
                <div className="text-xs text-orb-text-dim space-y-1">
                  <div className="flex justify-between">
                    <span>Status:</span>
                    <span className={result.drift?.status === 'ZERO_DRIFT' ? 'text-orb-success' : 'text-orb-warning'}>
                      {result.drift?.status || 'Unknown'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Total Pings:</span>
                    <span>{result.drift?.total_pings || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Drift Rate:</span>
                    <span>{(result.drift?.drift_rate || 0).toFixed(4)}</span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
