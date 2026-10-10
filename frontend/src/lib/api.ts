import type { components } from './api.generated';

type HealthStatus = components['schemas']['HealthStatus'];

export async function getReadiness(
  signal?: AbortSignal,
): Promise<HealthStatus> {
  const response = await fetch('/api/health/ready', { signal });
  if (!response.ok) throw new Error('Ataraxia is unavailable.');
  const body: HealthStatus = await response.json();
  if (body.status !== 'ok') throw new Error('Ataraxia is unavailable.');
  return body;
}
