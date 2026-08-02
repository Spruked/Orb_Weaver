import React from 'react';
import { 
  LayoutDashboard, Mic, Brain, Wrench, Palette, 
  BarChart3, Activity, MessageSquare, User, Shield,
  Volume2, ChevronRight, Radio
} from 'lucide-react';

const navItems = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'behavior', label: 'Behavior & Personality', icon: User },
  { id: 'speech', label: 'Speech & Listening', icon: Volume2 },
  { id: 'intelligence', label: 'Intelligence & Models', icon: Brain },
  { id: 'tools', label: 'Tools & Permissions', icon: Wrench },
  { id: 'appearance', label: 'Appearance & Motion', icon: Palette },
  { id: 'live_test', label: 'Live Test', icon: Radio },
  { id: 'conversations', label: 'Conversations', icon: MessageSquare },
  { id: 'statistics', label: 'Statistics', icon: BarChart3 },
  { id: 'diagnostics', label: 'Diagnostics', icon: Activity },
];

export default function Layout({ children, activePanel, onNavigate, user }) {
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <aside style={{ width: 260, background: 'var(--color-surface)', borderRight: '1px solid var(--color-border)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '20px 16px', borderBottom: '1px solid var(--color-border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: 'var(--color-accent)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Shield size={18} color="white" />
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: 14 }}>ORB Dock Station</div>
              <div className="text-xs text-muted">Owner Control Center v2.1</div>
            </div>
          </div>
        </div>

        <nav style={{ flex: 1, padding: '12px 10px', overflowY: 'auto' }}>
          {navItems.map(item => {
            const Icon = item.icon;
            const active = activePanel === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '9px 12px',
                  borderRadius: 8,
                  border: 'none',
                  background: active ? 'var(--color-accent)' : 'transparent',
                  color: active ? 'white' : 'var(--color-text-secondary)',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: 500,
                  marginBottom: 2,
                  transition: 'all 0.15s',
                  textAlign: 'left',
                }}
              >
                <Icon size={16} />
                {item.label}
                {active && <ChevronRight size={14} style={{ marginLeft: 'auto' }} />}
              </button>
            );
          })}
        </nav>

        <div style={{ padding: '12px 16px', borderTop: '1px solid var(--color-border-subtle)' }}>
          <div className="text-xs text-muted" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--color-success)' }} />
            Authority Online
          </div>
        </div>
      </aside>

      <main style={{ flex: 1, overflow: 'auto', background: 'var(--color-bg)' }}>
        {children}
      </main>
    </div>
  );
}
