import { describe, expect, test } from 'vitest';
import type { Allowance, Job, Today } from '../src/lib/api';
import { formatDateline, formatHour, formatMonth } from '../src/lib/format';
import {
  deferredUntil,
  hasActiveWork,
  requestBlock,
  todayPollInterval,
} from '../src/lib/jobs';
import {
  isAllowedImage,
  isWikipediaPage,
  wikipediaSearchUrl,
} from '../src/lib/links';
import { splitSections } from '../src/lib/sections';
import { smarten } from '../src/lib/typography';
import { newSessionId } from '../src/features/lesson/useReading';

describe('formatting', () => {
  test('dates read like an almanac', () => {
    expect(formatDateline('2026-11-24')).toBe('Tuesday, 24 November');
    expect(formatMonth('2026-11-01')).toBe('November 2026');
    expect(formatHour(6)).toBe('06:00');
  });
});

describe('typography', () => {
  test('sets quotes, apostrophes, dashes, and ellipses', () => {
    expect(smarten(`"It's here," she said -- 'quietly'...`, '')).toBe(
      '“It’s here,” she said – ‘quietly’…',
    );
    expect(smarten('rock --- and roll', '')).toBe('rock — and roll');
    expect(smarten("'90s", '')).toBe('‘90s');
    expect(smarten("s' own", 'x')).toBe('s’ own');
  });
});

describe('links', () => {
  test('further links are Wikipedia searches built from title and creator', () => {
    expect(
      wikipediaSearchUrl({ title: 'Tokyo Story', creator: 'Ozu & co' }),
    ).toBe(
      'https://en.wikipedia.org/w/index.php?search=Tokyo%20Story%20Ozu%20%26%20co',
    );
    expect(wikipediaSearchUrl({ title: 'Rijksmuseum' })).toBe(
      'https://en.wikipedia.org/w/index.php?search=Rijksmuseum',
    );
  });

  test('only Wikimedia images over HTTPS are shown', () => {
    expect(isAllowedImage('https://upload.wikimedia.org/a.jpg')).toBe(true);
    expect(isAllowedImage('https://thumb.wikimedia.org/a.jpg')).toBe(true);
    expect(isAllowedImage('http://upload.wikimedia.org/a.jpg')).toBe(false);
    expect(
      isAllowedImage('https://upload.wikimedia.org.evil.example/a.jpg'),
    ).toBe(false);
    expect(isAllowedImage('javascript:alert(1)')).toBe(false);
    expect(isWikipediaPage('https://en.wikipedia.org/wiki/X')).toBe(true);
    expect(isWikipediaPage('https://evil.example/wiki/X')).toBe(false);
  });
});

describe('sections', () => {
  test('splits at level-2 headings but not inside code', () => {
    const markdown =
      'Intro\n\n## One\n\nText\n\n```md\n## not a heading\n```\n\n## Two\n\nEnd';
    const sections = splitSections(markdown);
    expect(sections).toHaveLength(3);
    expect(sections[1]).toContain('## not a heading');
    expect(sections[2].startsWith('## Two')).toBe(true);
  });
});

describe('jobs', () => {
  const allowance = (fields: Partial<Allowance>): Allowance => ({
    used: 0,
    limit: 8,
    remaining: 8,
    waiting: 0,
    waiting_limit: 3,
    ...fields,
  });

  test('requests are blocked at the daily cap or with three waiting', () => {
    expect(requestBlock(allowance({}))).toBeNull();
    expect(requestBlock(allowance({ remaining: 0 }))).toMatch(/used up/);
    expect(requestBlock(allowance({ waiting: 3 }))).toMatch(
      /3 lessons are already/,
    );
  });

  test('only queued or running work keeps Today polling', () => {
    const today = (
      status: Today['daily']['status'],
      jobs: Partial<Job>[] = [],
    ) => ({ daily: { status }, jobs }) as unknown as Today;
    expect(hasActiveWork(undefined)).toBe(false);
    expect(hasActiveWork(today('ready'))).toBe(false);
    expect(hasActiveWork(today('running'))).toBe(true);
    expect(hasActiveWork(today('failed', [{ status: 'failed' }]))).toBe(false);
    expect(hasActiveWork(today('ready', [{ status: 'queued' }]))).toBe(true);
  });

  test('a queued job with a later attempt time is waiting', () => {
    const now = new Date('2026-11-24T10:00:00Z');
    const job = {
      status: 'queued',
      next_attempt_at: '2026-11-24T10:30:00Z',
    } as Job;
    expect(deferredUntil(job, now)).toBe('2026-11-24T10:30:00Z');
    expect(deferredUntil({ ...job, next_attempt_at: null }, now)).toBeNull();
  });
});

test('session IDs are UUIDs the API accepts', () => {
  expect(newSessionId()).toMatch(/^[0-9a-f-]{36}$/);
});

describe('Today polling interval', () => {
  const now = new Date('2026-11-24T10:00:00Z');
  const job = (fields: Partial<Job>) =>
    ({ status: 'queued', next_attempt_at: null, ...fields }) as Job;
  const today = (jobs: Job[]) =>
    ({ daily: { status: 'ready', job: null }, jobs }) as unknown as Today;

  test('polls quickly while a job can finish soon', () => {
    expect(
      todayPollInterval(today([job({ status: 'running' })]), now, 4000),
    ).toBe(4000);
  });

  test('polls once a minute while every waiting job is deferred', () => {
    const deferred = job({ next_attempt_at: '2026-11-24T10:25:00Z' });
    expect(todayPollInterval(today([deferred]), now, 4000)).toBe(60_000);
  });

  test('stops when nothing is waiting', () => {
    expect(todayPollInterval(today([]), now, 4000)).toBe(false);
  });
});
