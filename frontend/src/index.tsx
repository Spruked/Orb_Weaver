import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import AutonomousOrb from './landing/AutonomousOrb';
import { installLocalPointerFallbacks } from './orb/installLocalPointerFallbacks';

installLocalPointerFallbacks();

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <>
      <App />
      <AutonomousOrb size={156} />
    </>
  </React.StrictMode>
);
