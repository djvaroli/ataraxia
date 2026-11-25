/**
 * Start-up and sign-in: load the public client configuration, build the auth
 * client for its mode, then show sign-in or the app. API errors 401 and 403
 * from any query or mutation end up here.
 */
import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, createApiClient, getClientConfig } from '../lib/api';
import type { AuthClient, AuthUser } from '../lib/auth';
import { Forbidden, Opening, Unavailable } from '../features/auth/Blocked';
import { SignIn } from '../features/auth/SignIn';
import { AppRoutes } from './AppRoutes';
import {
  type AppDependencies,
  type Services,
  ServicesContext,
} from './services';

type BootState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; auth: AuthClient };

export function App({ deps }: { deps: AppDependencies }) {
  const [attempt, setAttempt] = useState(0);
  const [boot, setBoot] = useState<BootState>({ kind: 'loading' });
  // One start-up per attempt, even when StrictMode runs effects twice:
  // the Firebase app can only be initialised once.
  const started = useRef<{ attempt: number; done: Promise<AuthClient> } | null>(
    null,
  );

  useEffect(() => {
    if (started.current?.attempt !== attempt) {
      started.current = {
        attempt,
        done: getClientConfig(deps.fetch).then((config) =>
          deps.createAuth(config),
        ),
      };
    }
    let current = true;
    started.current.done.then(
      (auth) => current && setBoot({ kind: 'ready', auth }),
      (error: unknown) =>
        current &&
        setBoot({
          kind: 'error',
          message:
            error instanceof Error
              ? error.message
              : 'Ataraxia could not be reached.',
        }),
    );
    return () => {
      current = false;
    };
  }, [deps, attempt]);

  if (boot.kind === 'loading') return <Opening />;
  if (boot.kind === 'error') {
    return (
      <Unavailable
        message={boot.message}
        onRetry={() => {
          setBoot({ kind: 'loading' });
          setAttempt((value) => value + 1);
        }}
      />
    );
  }
  return <AuthGate auth={boot.auth} deps={deps} />;
}

function AuthGate({ auth, deps }: { auth: AuthClient; deps: AppDependencies }) {
  const [user, setUser] = useState<AuthUser | null | undefined>(undefined);
  const [forbidden, setForbidden] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(
    () =>
      auth.subscribe((next) => {
        setUser(next);
        if (next) setNotice(null);
      }),
    [auth],
  );

  const onApiError = useCallback(
    (error: unknown) => {
      if (!(error instanceof ApiError)) return;
      if (error.status === 403) {
        setForbidden(true);
      } else if (error.status === 401 && auth.mode === 'firebase') {
        setNotice('Your session ended. Sign in again.');
        void auth.signOut();
      }
    },
    [auth],
  );

  if (forbidden) {
    return (
      <Forbidden
        mode={auth.mode}
        onSignOut={() => {
          setForbidden(false);
          void auth.signOut();
        }}
      />
    );
  }
  if (user === undefined) return <Opening />;
  if (user === null) return <SignIn auth={auth} notice={notice} />;
  return (
    <SignedIn auth={auth} user={user} deps={deps} onApiError={onApiError} />
  );
}

function isTransient(error: unknown): boolean {
  return (
    error instanceof ApiError && (error.status === 0 || error.status >= 500)
  );
}

function SignedIn({
  auth,
  user,
  deps,
  onApiError,
}: {
  auth: AuthClient;
  user: AuthUser;
  deps: AppDependencies;
  onApiError: (error: unknown) => void;
}) {
  const [services] = useState<Services>(() => ({
    api: createApiClient(deps.fetch, () => auth.getToken()),
    auth,
    user,
    pollMs: deps.pollMs ?? 4000,
    now: deps.now ?? (() => new Date()),
  }));
  // A new client per sign-in, so nothing cached crosses accounts.
  const [client] = useState(
    () =>
      new QueryClient({
        queryCache: new QueryCache({ onError: onApiError }),
        mutationCache: new MutationCache({ onError: onApiError }),
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: (failures, error) => failures < 1 && isTransient(error),
          },
          mutations: { retry: false },
        },
      }),
  );
  useEffect(() => () => client.clear(), [client]);

  return (
    <ServicesContext value={services}>
      <QueryClientProvider client={client}>
        <AppRoutes />
      </QueryClientProvider>
    </ServicesContext>
  );
}
