import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import AutonomousOrb from './landing/AutonomousOrb';
import { installWebsiteOrbRuntimeGuards } from './orb/runtimeGuards';
import { authStore } from './services/api';
import './landing/orbVoiceOnly.css';

installWebsiteOrbRuntimeGuards({ authenticated: Boolean(authStore.getToken()) });

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <App />
      <AutonomousOrb size={156} />
    </BrowserRouter>
  </React.StrictMode>
);