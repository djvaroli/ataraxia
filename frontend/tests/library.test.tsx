import {
  screen,
  waitForElementToBeRemoved,
  within,
} from '@testing-library/react';
import { describe, expect, test } from 'vitest';
import { FakeServer } from '../src/fake/server';
import { NOW, renderApp } from './render';

describe('Library', () => {
  test('lists lessons newest first, grouped by month, with their marks', async () => {
    renderApp({ path: '/library' });

    const november = await screen.findByRole('heading', {
      name: 'November 2026',
    });
    const october = screen.getByRole('heading', { name: 'October 2026' });
    expect(
      november.compareDocumentPosition(october) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    const row = screen
      .getByRole('link', { name: /Five words for the end of the day/ })
      .closest('li') as HTMLElement;
    expect(within(row).getByText('Finished')).toBeVisible();
    expect(within(row).getByText('Saved')).toBeVisible();
    expect(within(row).getByText('Words')).toBeVisible();
    const part = screen
      .getByRole('link', { name: /open addressing/ })
      .closest('li') as HTMLElement;
    expect(within(part).getByText('Part 2')).toBeVisible();
  });

  test('filters by saved and by subject', async () => {
    const { server, user } = renderApp({ path: '/library' });
    await screen.findByRole('heading', { name: 'November 2026' });

    await user.click(screen.getByRole('button', { name: 'Saved' }));
    expect(
      await screen.findByRole('link', { name: /Middlemarch/ }),
    ).toBeVisible();
    expect(
      screen.queryByRole('link', { name: /hash table/ }),
    ).not.toBeInTheDocument();
    expect(server.requests.at(-1)?.path).toContain('saved=true');

    await user.click(screen.getByRole('button', { name: 'Computer science' }));
    expect(
      await screen.findByRole('link', { name: /hash table/ }),
    ).toBeVisible();
    expect(
      screen.queryByRole('link', { name: /Middlemarch/ }),
    ).not.toBeInTheDocument();
    expect(server.requests.at(-1)?.path).toContain('subject=computing');
    expect(
      screen.getByRole('button', { name: 'Computer science' }),
    ).toHaveAttribute('aria-pressed', 'true');
  });

  test('searches after typing pauses', async () => {
    const { server, user } = renderApp({ path: '/library' });
    await screen.findByRole('heading', { name: 'November 2026' });

    await user.type(
      screen.getByRole('searchbox', { name: 'Search the library' }),
      'Rosetta',
    );

    await waitForElementToBeRemoved(() =>
      screen.queryByRole('link', { name: /hash table/ }),
    );
    expect(screen.getByRole('link', { name: /Rosetta Stone/ })).toBeVisible();
    const searches = server.requests.filter((request) =>
      request.path.includes('q='),
    );
    expect(searches.map((request) => request.path)).toEqual([
      '/api/v1/lessons?q=Rosetta&limit=20',
    ]);
  });

  test('loads more with the cursor', async () => {
    const server = new FakeServer({ now: () => NOW });
    server.addOlderLessons(15);
    const { user } = renderApp({ server, path: '/library' });
    await screen.findByRole('heading', { name: 'November 2026' });
    expect(
      screen.queryByText(/sunsets are red \(15\)/),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Load more' }));

    expect(await screen.findByText(/sunsets are red \(15\)/)).toBeVisible();
    expect(server.requests.at(-1)?.path).toContain('cursor=20');
    expect(
      screen.queryByRole('button', { name: 'Load more' }),
    ).not.toBeInTheDocument();
  });

  test('says when nothing matches', async () => {
    const { user } = renderApp({ path: '/library' });
    await screen.findByRole('heading', { name: 'November 2026' });
    await user.type(screen.getByRole('searchbox'), 'zebra');
    expect(await screen.findByText('Nothing matches “zebra”.')).toBeVisible();
  });
});
