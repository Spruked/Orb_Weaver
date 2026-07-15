import { Routes, Route } from 'react-router-dom'
import { OrbLayout } from '@components/orb/OrbLayout'
import { PipelineDashboard } from '@components/pipeline_visualizer/PipelineDashboard'
import { VaultExplorer } from '@components/vault_viewer/VaultExplorer'
import { BeamMonitor } from '@components/philosopher_beams/BeamMonitor'
import { DriftConsole } from '@components/drift_monitor/DriftConsole'
import { CochlearPanel } from '@components/cochlear_panel/CochlearPanel'
import { TTSEngineSelector } from '@components/tts_engine_selector/TTSEngineSelector'

function App() {
  return (
    <>
      <div className="field-bg" />
      <div className="app app-container">
        <OrbLayout>
          <Routes>
            <Route path="/" element={<PipelineDashboard />} />
            <Route path="/vaults" element={<VaultExplorer />} />
            <Route path="/beams" element={<BeamMonitor />} />
            <Route path="/drift" element={<DriftConsole />} />
            <Route path="/cochlear" element={<CochlearPanel />} />
            <Route path="/tts" element={<TTSEngineSelector />} />
          </Routes>
        </OrbLayout>
      </div>
    </>
  )
}

export default App
