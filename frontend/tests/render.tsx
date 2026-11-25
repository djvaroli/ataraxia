import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { vi } from 'vitest';
import { App } from '../src/app/App';
import type { AppDependencies } from '../src/app/services';
import { FakeServer, type FakeServerOptions } from '../src/fake/server';
import { createLocalAuth, type AuthClient } from '../src/lib/auth';

export const NOW = new Date('2026-11-24T10:00:00Z');

interface RenderOptions {
  path?: string;
  server?: FakeServer;
  scenario?: FakeServerOptions['scenario'];
  auth?: AuthClient;
  pollMs?: number;
  /** Pass false when fake timers drive the clicks. */
  realTimers?: boolean;
}

export function renderApp(options: RenderOptions = {}) {
  const server =
    options.server ??
    new FakeServer({ now: () => NOW, scenario: options.scenario });
  const auth = options.auth ?? createLocalAuth();
  const deps: AppDependencies = {
    fetch: server.fetch,
    createAuth: async () => auth,
    pollMs: options.pollMs ?? 4000,
    now: () => NOW,
  };
  const user = userEvent.setup(
    options.realTimers === false
      ? { advanceTimers: (ms) => vi.advanceTimersByTime(ms) }
      : {},
  );
  const view = render(
    <MemoryRouter initialEntries={[options.path ?? '/']}>
      <App deps={deps} />
    </MemoryRouter>,
  );
  return { server, auth, user, ...view };
}

/** Request bodies sent to an endpoint, oldest first. */
export function bodies(server: FakeServer, method: string, path: RegExp) {
  return server.requestsTo(method, path).map((request) => request.body);
}
