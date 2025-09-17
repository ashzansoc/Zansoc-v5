import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import wsService from './services/websocket';

// Initialize WebSocket connection
wsService.connect();

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Cleanup on app unmount
window.addEventListener('beforeunload', () => {
  wsService.disconnect();
});