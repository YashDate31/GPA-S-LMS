import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import axios from 'axios'
import { getCsrfToken } from './utils/csrf'
import { registerSW } from 'virtual:pwa-register'

// --- CSRF Protection: Add token to all state-changing requests ---
axios.interceptors.request.use((config) => {
  const method = (config.method || 'get').toLowerCase();
  const url = String(config.url || '');

  // Add CSRF token for POST, PUT, DELETE, PATCH methods
  if (['post', 'put', 'delete', 'patch'].includes(method)) {
    const token = getCsrfToken();
    if (token) {
      config.headers['X-CSRF-Token'] = token;
    }
  }

  // Avoid stale API reads from browser/service-worker caches.
  // Keep catalogue caching behavior for /api/books; force fresh reads elsewhere.
  if (method === 'get' && url.startsWith('/api/') && !url.startsWith('/api/books')) {
    config.params = {
      ...(config.params || {}),
      _t: Date.now(),
    };
    config.headers['Cache-Control'] = 'no-cache';
    config.headers['Pragma'] = 'no-cache';
  }

  return config;
}, (error) => {
  return Promise.reject(error);
});

// --- PWA: auto-update + auto-reload on new version ---
// Prevent clients from being stuck on an old UI due to service worker caching.
const updateSW = registerSW({
  immediate: true,
  onNeedRefresh() {
    // Activate the new service worker and reload to fetch fresh assets.
    Promise.resolve(updateSW(true)).finally(() => {
      window.location.reload();
    });
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

