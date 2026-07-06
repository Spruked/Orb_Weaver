import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import AutonomousOrb from './landing/AutonomousOrb';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <>
      <App />
      <AutonomousOrb size={190} />
    </>
  </React.StrictMode>
);
