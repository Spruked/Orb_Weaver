import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import AutonomousOrb from './landing/AutonomousOrb';
import OrbStartupGreeting from './landing/OrbStartupGreeting';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <>
      <App />
      <OrbStartupGreeting />
      <AutonomousOrb size={156} />
    </>
  </React.StrictMode>
);
