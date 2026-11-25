/** The side-effecting dependencies screens use, chosen once at the composition root. */
import { createContext, useContext } from 'react';
import type { ApiClient, ClientConfig, FetchLike } from '../lib/api';
import type { AuthClient, AuthUser } from '../lib/auth';

export interface Services {
  api: ApiClient;
  auth: AuthClient;
  user: AuthUser;
  /** How often Today refreshes while a lesson is being prepared. */
  pollMs: number;
  now: () => Date;
}

/** What `main.tsx` (or a test) gives the app. */
export interface AppDependencies {
  fetch: FetchLike;
  createAuth: (config: ClientConfig) => Promise<AuthClient>;
  pollMs?: number;
  now?: () => Date;
}

export const ServicesContext = createContext<Services | null>(null);

export function useServices(): Services {
  const services = useContext(ServicesContext);
  if (!services) throw new Error('useServices needs a ServicesContext');
  return services;
}

export function useApi(): ApiClient {
  return useServices().api;
}
