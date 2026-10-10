import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test, vi } from 'vitest';
import { App } from '../src/app/App';

test('a failed connection can be retried without reloading the page', async () => {
  const request = vi
    .fn()
    .mockResolvedValueOnce(
      new Response('{"status":"unavailable"}', { status: 503 }),
    )
    .mockResolvedValueOnce(new Response('{"status":"ok"}'));
  vi.stubGlobal('fetch', request);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
  expect(screen.getByRole('status')).toHaveTextContent('Connecting');
  await userEvent.click(
    await screen.findByRole('button', { name: 'Try again' }),
  );
  expect(
    await screen.findByText('Connected. There’s room to grow.'),
  ).toBeVisible();
  expect(request).toHaveBeenLastCalledWith(
    '/api/health/ready',
    expect.objectContaining({ signal: expect.any(AbortSignal) }),
  );
  client.clear();
});
