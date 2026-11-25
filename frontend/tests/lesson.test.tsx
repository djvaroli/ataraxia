import { act, renderHook, screen, within } from '@testing-library/react';
import { useRef } from 'react';
import { describe, expect, test, vi } from 'vitest';
import { createFakeAuth } from '../src/fake/auth';
import { FakeServer } from '../src/fake/server';
import { useReadingReports } from '../src/features/lesson/useReading';
import { ApiError } from '../src/lib/api';
import { NOW, bodies, renderApp } from './render';

function serverWith(extraMarkdown = '') {
  const server = new FakeServer({ now: () => NOW, scenario: 'ready' });
  const lesson = server.lesson('l-harmonic');
  if (lesson) lesson.body_markdown += extraMarkdown;
  return server;
}

async function openLesson(id: string, server = serverWith()) {
  const result = renderApp({ server, path: `/lessons/${id}`, pollMs: 10 });
  await screen.findByRole('heading', { level: 1 });
  return result;
}

describe('Lesson reader', () => {
  test('renders headings, math, tables, and code, and keeps model output inert', async () => {
    const server = serverWith(
      '\n\nSee [a source](https://evil.example/x) or https://evil.example/y.\n\n<script>alert(1)</script><b>bold?</b>\n\n![pic](https://evil.example/p.png)\n\nIt\'s "quoted" -- here.',
    );
    const { container } = await openLesson('l-harmonic', server);

    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'Why adding ever-smaller steps can still take you anywhere',
      }),
    ).toBeVisible();
    expect(
      screen.getByRole('heading', { level: 2, name: 'Oresme’s argument' }),
    ).toBeVisible();
    expect(container.querySelector('.katex-display')).not.toBeNull();
    expect(screen.getByRole('region', { name: 'Table' })).toContainElement(
      screen.getAllByRole('table')[0],
    );
    expect(screen.getByText(/a source/)).toBeVisible();
    expect(container.querySelector('a[href*="evil.example"]')).toBeNull();
    expect(container.querySelector('img[src*="evil.example"]')).toBeNull();
    expect(container.querySelector('script, b')).toBeNull();
    expect(screen.getByText(/It’s “quoted” – here\./)).toBeVisible();
    expect(
      server.requestsTo('POST', /\/lessons\/l-harmonic\/opened$/),
    ).toHaveLength(1);
  });

  test('shows where a lesson sits in its thread', async () => {
    await openLesson('l-hash-2');
    expect(screen.getByText('Part 2 of 2')).toBeVisible();
    const thread = screen.getByRole('navigation', { name: 'This thread' });
    expect(
      within(thread).getByRole('link', {
        name: 'How a hash table finds anything in one step',
      }),
    ).toHaveAttribute('href', '/lessons/l-hash');
  });

  test('renders code blocks as focusable, scrollable monospace', async () => {
    const { container } = await openLesson('l-hash');
    const pre = container.querySelector('pre');
    expect(pre).toHaveAttribute('tabindex', '0');
    expect(pre?.querySelector('code')).toHaveTextContent('class HashTable:');
  });

  test('never scales a small illustration past its natural width', async () => {
    const { container } = await openLesson('l-ozu');
    const poster = container.querySelector('img');
    expect(poster).toHaveAttribute('width', '250');
    expect(poster?.src).toMatch(/^https:\/\/thumb\.wikimedia\.org\//);
  });

  test('builds illustration and further links only from trusted sources', async () => {
    const { container } = await openLesson('l-vermeer');
    const images = container.querySelectorAll('img');
    expect(images.length).toBeGreaterThan(0);
    images.forEach((image) => {
      expect(image.src).toMatch(/^https:\/\/(upload|thumb)\.wikimedia\.org\//);
      expect(image).toHaveAttribute('referrerpolicy', 'no-referrer');
    });
    const further = screen.getByRole('link', { name: /Vermeer’s Camera/ });
    expect(further).toHaveAttribute(
      'href',
      'https://en.wikipedia.org/w/index.php?search=Vermeer%E2%80%99s%20Camera%20Philip%20Steadman',
    );
    expect(further).toHaveAttribute('rel', 'noreferrer noopener');
    expect(further).toHaveAttribute('target', '_blank');
  });

  test('saves, rates, and finishes a lesson', async () => {
    const { server, user } = await openLesson('l-vermeer');

    const [topSave] = screen.getAllByRole('button', {
      name: 'Save',
      pressed: false,
    });
    await user.click(topSave);
    expect(bodies(server, 'PUT', /\/saved$/)).toEqual([{ saved: true }]);
    expect(
      await screen.findAllByRole('button', { name: 'Saved' }),
    ).toHaveLength(2);

    const more = screen.getByRole('button', { name: 'More like this' });
    await user.click(more);
    expect(more).toHaveAttribute('aria-pressed', 'true');
    await user.click(more);
    expect(more).toHaveAttribute('aria-pressed', 'false');
    await user.click(screen.getByRole('button', { name: 'Less like this' }));
    expect(bodies(server, 'PUT', /\/rating$/)).toEqual([
      { rating: 1 },
      { rating: 0 },
      { rating: -1 },
    ]);

    await user.click(screen.getByRole('button', { name: 'Mark as finished' }));
    expect(bodies(server, 'PUT', /\/finished$/)).toEqual([{ finished: true }]);
    expect(
      await screen.findByRole('button', { name: 'Finished' }),
    ).toHaveAttribute('aria-pressed', 'true');
  });

  test('rolls back a change the server refuses', async () => {
    const { server, user } = await openLesson('l-vermeer');
    server.failNext({
      method: 'PUT',
      path: /\/finished$/,
      status: 404,
      code: 'not_found',
      message: 'No such lesson.',
    });
    await user.click(screen.getByRole('button', { name: 'Mark as finished' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No such lesson.',
    );
    expect(
      screen.getByRole('button', { name: 'Mark as finished' }),
    ).toBeVisible();
  });

  test('requests a follow-up and shows when it is ready', async () => {
    const { server, user } = await openLesson('l-vermeer');

    await user.click(screen.getByRole('button', { name: /^Vermeer’s blues/ }));
    const sheet = screen.getByRole('dialog', { name: 'Go deeper' });
    await user.click(
      within(sheet).getByRole('button', { name: 'Prepare part 2' }),
    );

    expect(bodies(server, 'POST', /\/follow-ups$/)).toEqual([{ direction: 0 }]);
    expect(await within(sheet).findByText('Preparing part 2…')).toBeVisible();

    server.advanceJobs();
    server.advanceJobs();
    await user.click(
      await within(sheet).findByRole('button', { name: 'Open part 2' }),
    );
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Vermeer’s blues' }),
    ).toBeVisible();
    expect(screen.getByText('Part 2 of 2')).toBeVisible();
  });

  test('asks a question of its own', async () => {
    const { server, user } = await openLesson('l-vermeer');
    await user.click(
      screen.getByRole('button', { name: /Ask your own question/ }),
    );
    const sheet = screen.getByRole('dialog', { name: 'Go deeper' });
    const submit = within(sheet).getByRole('button', {
      name: 'Prepare part 2',
    });
    expect(submit).toBeDisabled();
    await user.type(
      within(sheet).getByRole('textbox', { name: 'Your question' }),
      'Why was ultramarine so costly?',
    );
    await user.click(submit);
    expect(bodies(server, 'POST', /\/follow-ups$/)).toEqual([
      { question: 'Why was ultramarine so costly?' },
    ]);
  });

  test('flags a problem with a note', async () => {
    const { server, user } = await openLesson('l-vermeer');
    await user.click(screen.getByRole('button', { name: 'More' }));
    await user.click(screen.getByRole('menuitem', { name: 'Flag a problem' }));
    const sheet = screen.getByRole('dialog', { name: 'Flag a problem' });
    await user.type(
      within(sheet).getByRole('textbox'),
      'The date looks wrong.',
    );
    await user.click(
      within(sheet).getByRole('button', { name: 'Flag this lesson' }),
    );
    expect(bodies(server, 'PUT', /\/flag$/)).toEqual([
      { note: 'The date looks wrong.' },
    ]);
    expect(
      await within(sheet).findByText(/recorded for later review/),
    ).toBeVisible();
  });

  test('says when a lesson does not exist', async () => {
    renderApp({ path: '/lessons/nope' });
    expect(await screen.findByText('This lesson doesn’t exist.')).toBeVisible();
  });
});

describe('Reading reports', () => {
  function setVisibility(state: DocumentVisibilityState) {
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => state,
    });
    document.dispatchEvent(new Event('visibilitychange'));
  }

  test('reports cumulative visible time every 30 s, on hide, and on close', () => {
    vi.useFakeTimers();
    setVisibility('visible');
    const send = vi.fn(() => Promise.resolve());
    const { unmount } = renderHook(() => {
      const ref = useRef<HTMLDivElement>(document.createElement('div'));
      useReadingReports('l-1', ref, send);
    });

    act(() => vi.advanceTimersByTime(30_000));
    expect(send).toHaveBeenCalledTimes(1);
    const [first] = send.mock.calls[0] as unknown as [
      { session_id: string; seconds: number; scroll: number },
    ];
    expect(first.session_id).toMatch(/^[0-9a-f-]{36}$/);
    expect(first.seconds).toBe(30);

    act(() => vi.advanceTimersByTime(10_000));
    act(() => setVisibility('hidden'));
    expect(send).toHaveBeenLastCalledWith(
      expect.objectContaining({ session_id: first.session_id, seconds: 40 }),
    );

    // Hidden time does not count, and no report is sent while hidden.
    act(() => vi.advanceTimersByTime(120_000));
    expect(send).toHaveBeenCalledTimes(2);

    act(() => setVisibility('visible'));
    act(() => vi.advanceTimersByTime(5_000));
    unmount();
    expect(send).toHaveBeenCalledTimes(3);
    expect(send).toHaveBeenLastCalledWith(
      expect.objectContaining({ session_id: first.session_id, seconds: 45 }),
    );
  });

  test('starts a new session when the server says the ID belongs to another lesson', async () => {
    vi.useFakeTimers();
    setVisibility('visible');
    const conflict = new ApiError(
      409,
      'conflict',
      'Session used for another lesson.',
    );
    const send = vi
      .fn<(report: { session_id: string; seconds: number }) => Promise<void>>()
      .mockRejectedValueOnce(conflict)
      .mockResolvedValue(undefined);
    renderHook(() => {
      const ref = useRef<HTMLDivElement>(document.createElement('div'));
      useReadingReports('l-1', ref, send);
    });

    await act(() => vi.advanceTimersByTimeAsync(30_000));
    await act(() => vi.advanceTimersByTimeAsync(30_000));
    const [first, second] = send.mock.calls.map(([report]) => report);
    expect(second.session_id).not.toBe(first.session_id);
    expect(second.seconds).toBe(60);
  });

  test('sends reading reports with keepalive and the bearer token', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] });
    vi.setSystemTime(NOW);
    setVisibility('visible');
    const server = serverWith();
    const auth = createFakeAuth({ signedIn: true });
    renderApp({ server, auth, path: '/lessons/l-vermeer' });
    await screen.findByRole('heading', { level: 1 });
    await act(() => vi.advanceTimersByTimeAsync(30_000));
    const [report] = server.requestsTo('POST', /\/reading$/);
    expect(report.keepalive).toBe(true);
    expect(report.authorization).toBe('Bearer fake-id-token');
    expect(report.body).toMatchObject({ seconds: 30 });
  });
});
