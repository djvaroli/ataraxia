import { screen, waitFor, within } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';
import { createFakeAuth } from '../src/fake/auth';
import { bodies, renderApp } from './render';

describe('Settings', () => {
  test('sets the browser’s time zone on first run', async () => {
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const { server } = renderApp({ scenario: 'new' });
    await waitFor(() =>
      expect(bodies(server, 'PATCH', /\/me$/)).toEqual([{ time_zone: zone }]),
    );
    expect(server.me.preferences.time_zone_confirmed).toBe(true);
  });

  test('does not touch a confirmed time zone', async () => {
    const { server } = renderApp({ scenario: 'ready' });
    await screen.findByText('Another lesson');
    expect(server.requestsTo('PATCH', /\/me$/)).toHaveLength(0);
  });

  test('saves each change and keeps at least one subject', async () => {
    const { server, user } = renderApp({ path: '/settings' });
    const subjects = await screen.findByRole('group', { name: 'Subjects' });

    await user.click(within(subjects).getByRole('checkbox', { name: /^Art/ }));
    expect(await screen.findByText('Saved.')).toBeVisible();
    expect(bodies(server, 'PATCH', /\/me$/)[0]).toEqual({
      subjects: server.me.catalog
        .map((subject) => subject.id)
        .filter((id) => id !== 'art'),
    });
    expect(
      within(subjects).getByRole('checkbox', { name: /^Art/ }),
    ).not.toBeChecked();

    await user.click(screen.getByRole('radio', { name: /Long/ }));
    await user.selectOptions(
      screen.getByRole('combobox', { name: 'Ready by' }),
      '07:00',
    );
    await user.click(
      screen.getByRole('checkbox', { name: /Prepare a lesson each morning/ }),
    );
    expect(bodies(server, 'PATCH', /\/me$/).slice(1)).toEqual([
      { lesson_length: 'long' },
      { morning_hour: 7 },
      { morning_lesson: false },
    ]);
    expect(screen.getByRole('combobox', { name: 'Ready by' })).toBeDisabled();
  });

  test('disables the last enabled subject', async () => {
    const { server } = renderApp({ path: '/settings', scenario: 'ready' });
    server.me.preferences.subjects = ['music'];
    const music = await screen.findByRole('checkbox', { name: /^Music/ });
    expect(music).toBeChecked();
    expect(music).toBeDisabled();
  });

  test('reports a change that was not saved and shows the stored value', async () => {
    const { server, user } = renderApp({ path: '/settings' });
    server.failNext({
      method: 'PATCH',
      path: /\/me$/,
      status: 422,
      code: 'validation_failed',
      message: 'Unknown time zone.',
    });
    await user.click(await screen.findByRole('radio', { name: /Short/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Not saved: Unknown time zone.',
    );
    expect(screen.getByRole('radio', { name: /Standard/ })).toBeChecked();
  });

  test('downloads the export through the authenticated client', async () => {
    const createObjectURL = vi.fn(() => 'blob:export');
    vi.stubGlobal(
      'URL',
      Object.assign(URL, { createObjectURL, revokeObjectURL: vi.fn() }),
    );
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});
    const auth = createFakeAuth({ signedIn: true });
    const { server, user } = renderApp({ path: '/settings', auth });

    await user.click(
      await screen.findByRole('button', { name: 'Download export' }),
    );

    await waitFor(() => expect(click).toHaveBeenCalledTimes(1));
    const [request] = server.requestsTo('GET', /\/export$/);
    expect(request.authorization).toBe('Bearer fake-id-token');
    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    const link = click.mock.contexts[0] as HTMLAnchorElement;
    expect(link.download).toBe('ataraxia-export-2026-11-24.json');
  });

  test('shows local mode discreetly and has no sign-out', async () => {
    renderApp({ path: '/settings' });
    expect(await screen.findByText(/Local mode: no sign-in/)).toBeVisible();
    expect(
      screen.queryByRole('button', { name: 'Sign out' }),
    ).not.toBeInTheDocument();
  });

  test('signs out in firebase mode', async () => {
    const auth = createFakeAuth({ signedIn: true });
    const { user } = renderApp({ path: '/settings', auth });
    expect(await screen.findByText('owner@example.com')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Sign out' }));
    expect(
      await screen.findByRole('button', { name: 'Sign in' }),
    ).toBeVisible();
    expect(auth.signedIn()).toBe(false);
  });
});
