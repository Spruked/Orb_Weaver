import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  Orbit, Database, GitBranch, Activity, 
  Ear, Volume2, Menu, X 
} from 'lucide-react'

interface OrbLayoutProps {
  children: React.ReactNode
}

export function OrbLayout({ children }: OrbLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const location = useLocation()

  const navItems = [
    { path: '/', icon: Orbit, label: 'Pipeline', color: 'text-orb-accent' },
    { path: '/vaults', icon: Database, label: 'Vaults', color: 'text-orb-success' },
    { path: '/beams', icon: GitBranch, label: 'Beams', color: 'text-orb-hume' },
    { path: '/drift', icon: Activity, label: 'Drift', color: 'text-orb-warning' },
    { path: '/cochlear', icon: Ear, label: 'Cochlear', color: 'text-orb-kant' },
    { path: '/tts', icon: Volume2, label: 'TTS', color: 'text-orb-locke' },
  ]

  return (
    <div className="flex h-screen w-screen bg-orb-bg">
      {/* Sidebar */}
      <aside className={`
        ${sidebarOpen ? 'w-64' : 'w-16'}
        bg-orb-panel border-r border-orb-border
        transition-all duration-300 flex flex-col
      `}>
        {/* Header */}
        <div className="p-4 border-b border-orb-border flex items-center justify-between">
          {sidebarOpen && (
            <div className="flex items-center gap-2">
              <Orbit className="w-6 h-6 text-orb-accent" />
              <span className="font-bold text-orb-text">TPC Website ORB</span>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1 rounded hover:bg-orb-border text-orb-text-dim"
          >
            {sidebarOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-2 space-y-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path
            const Icon = item.icon
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`
                  flex items-center gap-3 px-3 py-2 rounded-lg
                  transition-colors duration-200
                  ${isActive 
                    ? 'bg-orb-accent/20 text-orb-accent' 
                    : 'text-orb-text-dim hover:bg-orb-border hover:text-orb-text'
                  }
                `}
              >
                <Icon className={`w-5 h-5 ${isActive ? item.color : ''}`} />
                {sidebarOpen && <span className="text-sm">{item.label}</span>}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        {sidebarOpen && (
          <div className="p-4 border-t border-orb-border">
            <div className="text-xs text-orb-text-dim">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-2 h-2 rounded-full bg-orb-success pulse-glow" />
                <span>System Active</span>
              </div>
              <div>v1.0.0 | TPC Architecture</div>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  )
}
