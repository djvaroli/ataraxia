/** Composition root: chooses the real or demo dependencies and starts the app. */
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import { App } from './app/App';
import './app/global.css';
import type { AppDependencies } from './app/services';
import type { ClientConfig } from './lib/api';
import { createLocalAuth } from './lib/auth';

async function createAuth(config: ClientConfig) {
  if (config.auth_mode === 'local') return createLocalAuth();
  if (!config.firebase) {
    throw new Error('Firebase sign-in is not configured on the server.');
  }
  const { createFirebaseAuth } = await import('./lib/firebaseAuth');
  return createFirebaseAuth(config.firebase);
}

async function dependencies(): Promise<AppDependencies> {
  // Vite replaces the flag at build time, so the demo is dropped from normal builds.
  if (import.meta.env.VITE_DEMO === '1') {
    const { demoDependencies } = await import('./fake/demo');
    return demoDependencies(window.location.search);
  }
  return { fetch: (input, init) => window.fetch(input, init), createAuth };
}

void dependencies().then((deps) => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <BrowserRouter>
        <App deps={deps} />
      </BrowserRouter>
    </StrictMode>,
  );
});
