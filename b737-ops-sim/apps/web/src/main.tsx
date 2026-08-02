import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App.js';
import { inputManager } from './input/inputManager.js';
import { startConnection } from './state/connection.js';
import './styles.css';

startConnection();
inputManager.start();

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
