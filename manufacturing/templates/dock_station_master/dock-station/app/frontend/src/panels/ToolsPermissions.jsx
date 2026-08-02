import React, { useState, useEffect } from 'react';
import { tools } from '../services/api';
import { ShieldCheck, ShieldAlert } from 'lucide-react';

export default function ToolsPermissions({ profileId }) {
  const [toolList, setToolList] = useState([]);

  useEffect(() => { if (profileId) load(); }, [profileId]);

  async function load() {
    const data = await tools.get(profileId);
    setToolList(data);
  }

  async function toggleTool(id) {
    const updated = toolList.map(t => 
      t.id === id ? { ...t, enabled: !t.enabled } : t
    );
    await tools.update(profileId, updated);
    setToolList(updated);
  }

  const categories = [...new Set(toolList.map(t => t.category))];

  return (
    <div className="p-6" style={{ maxWidth: 900 }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Tools & Permissions</h1>
      <p className="text-secondary mb-6">
        Selecting a tool here does <strong>not</strong> authorize its execution at runtime. 
        The Stage Governor still validates every action.
      </p>

      <div className="flex flex-col gap-4">
        {categories.map(cat => (
          <div key={cat} className="card">
            <div className="card-title mb-3" style={{ textTransform: 'capitalize' }}>{cat}</div>
            <div className="flex flex-col gap-2">
              {toolList.filter(t => t.category === cat).map(tool => (
                <div key={tool.id} className="flex items-center gap-3 p-3 rounded-md" style={{ background: 'var(--color-surface-raised)' }}>
                  <div 
                    className={`toggle ${tool.enabled ? 'active' : ''}`}
                    onClick={() => toggleTool(tool.id)}
                    style={{ flexShrink: 0 }}
                  />
                  <div style={{ flex: 1 }}>
                    <div className="text-sm font-medium">{tool.name}</div>
                    <div className="text-xs text-muted">{tool.description}</div>
                  </div>
                  {tool.requires_approval ? (
                    <span className="badge badge-warning flex items-center gap-1">
                      <ShieldAlert size={10} /> Approval required
                    </span>
                  ) : (
                    <span className="badge badge-healthy flex items-center gap-1">
                      <ShieldCheck size={10} /> Auto
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
