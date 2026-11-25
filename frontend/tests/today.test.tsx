import { act, screen, within } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';
import { FakeServer } from '../src/fake/server';
import { NOW, bodies, renderApp } from './render';

describe('Today', () => {
  test('shows the dateline, issue number, and the ready lesson as the cover', async () => {
    const { server } = renderApp({ scenario: 'ready' });

    expect(
      await screen.findByRole('heading', {
        level: 1,
        name: /Tuesday, 24 November/,
      }),
    ).toBeVisible();
    expect(await screen.findByText(/^No\. \d+$/)).toBeVisible();
    const cover = screen.getByRole('article', {
      name: 'What Vermeer’s Milkmaid does with a single window',
    });
    expect(
      within(cover).getByRole('link', { name: /Begin reading/ }),
    ).toHaveAttribute('href', '/lessons/l-vermeer');
    expect(screen.getByText('“the history of the semicolon”')).toBeVisible();
    expect(screen.getByText('Being written…')).toBeVisible();
    expect(bodies(server, 'POST', /\/activity$/)).toEqual([
      { type: 'app.opened' },
    ]);
  });

  test('starts the daily lesson when none is scheduled', async () => {
    const { server, user } = renderApp({ scenario: 'not_scheduled' });

    await user.click(
      await screen.findByRole('button', { name: 'Start today’s lesson' }),
    );

    expect(server.requestsTo('POST', /\/today\/lesson$/)).toHaveLength(1);
    expect(await screen.findByText('Preparing…')).toBeVisible();
  });

  test('says when the morning lesson will arrive', async () => {
    renderApp({ scenario: 'waiting' });
    expect(await screen.findByText('Arrives at 23:00.')).toBeVisible();
    expect(
      screen.getByRole('button', { name: 'Start today’s lesson' }),
    ).toBeEnabled();
  });

  test('explains a failure in plain words and retries it', async () => {
    const { server, user } = renderApp({ scenario: 'failed' });

    expect(await screen.findByText('It couldn’t be prepared.')).toBeVisible();
    expect(
      screen.getByText(/Claude is not signed in on the server/),
    ).toBeVisible();
    expect(screen.getByText(/claude auth login/)).toBeVisible();

    await user.click(screen.getByRole('button', { name: 'Retry' }));

    expect(server.requestsTo('POST', /\/jobs\/[^/]+\/retry$/)).toHaveLength(1);
    expect(await screen.findByText('Preparing…')).toBeVisible();
  });

  test('polls while a lesson is being prepared and stops when it is ready', async () => {
    vi.useFakeTimers({
      toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval'],
    });
    const server = new FakeServer({ now: () => NOW, scenario: 'preparing' });
    renderApp({ server, realTimers: false });
    const todayRequests = () => server.requestsTo('GET', /\/today$/).length;

    // Let start-up and the first fetch settle; each step may schedule the next.
    for (let step = 0; step < 20; step += 1) {
      await act(() => vi.advanceTimersByTimeAsync(10));
    }
    expect(screen.getByText('Preparing…')).toBeVisible();
    const first = todayRequests();

    await act(() => vi.advanceTimersByTimeAsync(4000));
    expect(todayRequests()).toBe(first + 1);

    server.advanceJobs(); // the worker finishes
    await act(() => vi.advanceTimersByTimeAsync(4000));
    expect(screen.getByRole('link', { name: /Begin reading/ })).toBeVisible();
    expect(screen.queryByText('Preparing…')).not.toBeInTheDocument();
    const settled = todayRequests();

    await act(() => vi.advanceTimersByTimeAsync(40_000));
    expect(todayRequests()).toBe(settled);
  });

  test('shows the allowance only when it is nearly used up', async () => {
    const server = new FakeServer({
      now: () => NOW,
      scenario: 'not_scheduled',
    });
    renderApp({ server });
    await screen.findByText('Another lesson');
    expect(screen.queryByText(/left today/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Surprise me' })).toBeEnabled();
  });

  test('disables requests when the day’s lessons are used up and shows a usage-limit wait', async () => {
    renderApp({ scenario: 'limit' });

    expect(
      await screen.findByText('Today’s lessons are used up. More tomorrow.'),
    ).toBeVisible();
    expect(screen.getByRole('button', { name: 'Surprise me' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Mathematics' })).toBeDisabled();
    expect(
      screen.getByText(/usage limit was reached\. Trying again at/),
    ).toBeVisible();
    expect(screen.getByText(/login on the server ends on/)).toBeVisible();
  });

  test('requests a lesson on any topic and lists it as waiting', async () => {
    const { server, user } = renderApp({ scenario: 'ready' });

    expect(await screen.findByText('2 lessons left today.')).toBeVisible();
    const box = screen.getByRole('textbox', { name: 'Or ask about anything' });
    await user.type(box, 'x');
    expect(screen.getByRole('button', { name: 'Ask' })).toBeDisabled();
    await user.clear(box);
    await user.type(box, '  how bridges stand up  ');
    await user.click(screen.getByRole('button', { name: 'Ask' }));

    expect(bodies(server, 'POST', /\/lessons\/requests$/)).toEqual([
      { kind: 'topic', topic: 'how bridges stand up' },
    ]);
    expect(await screen.findByText('“how bridges stand up”')).toBeVisible();
    expect(box).toHaveValue('');
  });

  test('reports a refused request', async () => {
    const { server, user } = renderApp({ scenario: 'ready' });
    server.failNext({
      method: 'POST',
      path: /\/lessons\/requests$/,
      status: 429,
      code: 'too_many_waiting',
      message: 'Three lessons are already being prepared.',
    });

    await user.click(
      await screen.findByRole('button', { name: 'Surprise me' }),
    );

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Three lessons are already being prepared.',
    );
  });

  test('warns when the worker is offline', async () => {
    const server = new FakeServer({ now: () => NOW, scenario: 'ready' });
    server.worker = {
      online: false,
      heartbeat_at: null,
      login_expires_at: null,
    };
    renderApp({ server });
    expect(
      await screen.findByText(/lesson worker isn’t running/),
    ).toBeVisible();
  });
});
