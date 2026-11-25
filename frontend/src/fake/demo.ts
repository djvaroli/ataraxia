/**
 * Demo mode (VITE_DEMO=1): the app runs against the in-memory API so it can be
 * seen without the backend. Only imported behind that flag, so production
 * builds leave it out.
 *
 * Query parameters on first load pick the state to show:
 *   ?scenario=ready|preparing|failed|waiting|not_scheduled|limit|new
 *   ?auth=firebase   start signed out (sign in with owner@example.com / "correct horse")
 */
import type { AppDependencies } from '../app/services';
import { createLocalAuth } from '../lib/auth';
import { createFakeAuth } from './auth';
import { FakeServer, type Scenario } from './server';

const SCENARIOS: Scenario[] = [
  'ready',
  'preparing',
  'failed',
  'waiting',
  'not_scheduled',
  'limit',
  'new',
];

export function demoDependencies(search: string): AppDependencies {
  const params = new URLSearchParams(search);
  const requested = params.get('scenario');
  const scenario = SCENARIOS.find((item) => item === requested) ?? 'ready';
  const firebase = params.get('auth') === 'firebase';
  const server = new FakeServer({
    scenario,
    authMode: firebase ? 'firebase' : 'local',
    advanceEveryMs: params.get('advance') === 'off' ? undefined : 7000,
    latency: 120,
  });
  return {
    fetch: server.fetch,
    createAuth: async (config) =>
      config.auth_mode === 'local' ? createLocalAuth() : createFakeAuth(),
  };
}
