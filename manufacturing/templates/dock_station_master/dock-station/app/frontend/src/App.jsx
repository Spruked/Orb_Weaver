import React, { useState, useEffect } from 'react';
import { auth } from './services/api';
import Layout from './components/Layout';
import Overview from './panels/Overview';
import SpeechListening from './panels/SpeechListening';
import BehaviorPersonality from './panels/BehaviorPersonality';
import IntelligenceModels from './panels/IntelligenceModels';
import ToolsPermissions from './panels/ToolsPermissions';
import AppearanceMotion from './panels/AppearanceMotion';
import LiveTest from './panels/LiveTest';
import Statistics from './panels/Statistics';
import Diagnostics from './panels/Diagnostics';
import Conversations from './panels/Conversations';

function Login({ onLogin }) {
  const [email, setEmail] = useState('owner@orb.system');
  const [password, setPassword] = useState('orb-owner-2026');
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    try {
      const res = await auth.login(email, password);
      localStorage.setItem('orb_token', res.access_token);
      onLogin(res);
    } catch (err) {
      setError('Invalid credentials');
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--color-bg)' }}>
      <div className="card" style={{ width: 360 }}>
        <h2 style={{ marginBottom: 4, fontSize: 20 }}>ORB Dock Station</h2>
        <p className="text-secondary" style={{ marginBottom: 24, fontSize: 13 }}>Owner authentication required</p>
        <form onSubmit={submit} className="flex flex-col gap-3">
          <input className="input" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
          <input className="input" type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} />
          {error && <p className="text-danger text-sm">{error}</p>}
          <button className="btn btn-primary" type="submit">Sign In</button>
        </form>
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [activePanel, setActivePanel] = useState('overview');
  const [profileId, setProfileId] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('orb_token');
    if (token) setUser({ token });
  }, []);

  if (!user) return <Login onLogin={setUser} />;

  const panels = {
    overview: <Overview onSelectProfile={setProfileId} activeProfile={profileId} />,
    behavior: <BehaviorPersonality profileId={profileId} />,
    speech: <SpeechListening profileId={profileId} />,
    intelligence: <IntelligenceModels profileId={profileId} />,
    tools: <ToolsPermissions profileId={profileId} />,
    appearance: <AppearanceMotion profileId={profileId} />,
    live_test: <LiveTest profileId={profileId} />,
    statistics: <Statistics profileId={profileId} />,
    diagnostics: <Diagnostics />,
    conversations: <Conversations profileId={profileId} />,
  };

  return (
    <Layout activePanel={activePanel} onNavigate={setActivePanel} user={user}>
      {panels[activePanel] || panels.overview}
    </Layout>
  );
}
