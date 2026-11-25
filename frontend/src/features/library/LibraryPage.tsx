import { keepPreviousData, useInfiniteQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { keys, useMe } from '../../app/queries';
import { useApi } from '../../app/services';
import { LessonRow } from '../../components/LessonRow';
import { PageHeader } from '../../components/PageHeader';
import ui from '../../components/ui.module.css';
import type { LessonFilters, LessonSummary, SubjectId } from '../../lib/api';
import { formatMonth } from '../../lib/format';
import { useDebounced } from '../../lib/useDebounced';
import styles from './library.module.css';

type Filter = 'all' | 'saved' | SubjectId;

const PAGE_SIZE = 20;
const SEARCH_DELAY_MS = 300;

function groupByMonth(lessons: LessonSummary[]) {
  const groups: { month: string; lessons: LessonSummary[] }[] = [];
  for (const lesson of lessons) {
    const month = formatMonth(lesson.local_date);
    const last = groups.at(-1);
    if (last?.month === month) last.lessons.push(lesson);
    else groups.push({ month, lessons: [lesson] });
  }
  return groups;
}

export function LibraryPage() {
  const api = useApi();
  const me = useMe();
  const [filter, setFilter] = useState<Filter>('all');
  const [search, setSearch] = useState('');
  const q = useDebounced(search.trim().slice(0, 100), SEARCH_DELAY_MS);

  const filters: LessonFilters = {
    ...(filter === 'saved' ? { saved: true } : {}),
    ...(filter !== 'all' && filter !== 'saved' ? { subject: filter } : {}),
    ...(q ? { q } : {}),
  };
  const lessons = useInfiniteQuery({
    queryKey: keys.lessons({ ...filters, limit: PAGE_SIZE }),
    queryFn: ({ pageParam, signal }) =>
      api.listLessons(
        { ...filters, cursor: pageParam, limit: PAGE_SIZE },
        signal,
      ),
    initialPageParam: null as string | null,
    getNextPageParam: (page) => page.next_cursor,
    placeholderData: keepPreviousData,
  });

  const items = lessons.data?.pages.flatMap((page) => page.items) ?? [];
  const groups = groupByMonth(items);
  const chips: { value: Filter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'saved', label: 'Saved' },
    ...(me.data?.catalog ?? []).map((subject) => ({
      value: subject.id,
      label: subject.label,
    })),
  ];

  return (
    <>
      <PageHeader title="Library" />
      <div className={styles.controls}>
        <label className={styles.search}>
          <span className="visually-hidden">Search the library</span>
          <input
            className={ui.input}
            type="search"
            placeholder="Search titles, hooks, and tags"
            maxLength={100}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <div className={styles.filters} role="group" aria-label="Filter">
          {chips.map((chip) => (
            <button
              key={chip.value}
              type="button"
              data-subject={
                chip.value === 'all' || chip.value === 'saved'
                  ? undefined
                  : chip.value
              }
              className={styles.filter}
              aria-pressed={filter === chip.value}
              onClick={() => setFilter(chip.value)}
            >
              {chip.label}
            </button>
          ))}
        </div>
      </div>

      <div aria-busy={lessons.isFetching} aria-live="polite">
        {lessons.isPending ? (
          <p className={styles.empty}>Opening the library…</p>
        ) : lessons.isError ? (
          <div className={styles.empty}>
            <p className={ui.notice} role="alert">
              {lessons.error.message}
            </p>
            <button
              type="button"
              className={ui.button}
              onClick={() => void lessons.refetch()}
            >
              Try again
            </button>
          </div>
        ) : items.length === 0 ? (
          <p className={styles.empty}>
            {q
              ? `Nothing matches “${q}”.`
              : filter === 'saved'
                ? 'Nothing saved yet. Use the bookmark in a lesson to keep it here.'
                : filter === 'all'
                  ? 'No lessons yet. The first one will appear here.'
                  : 'No lessons in this subject yet.'}
          </p>
        ) : (
          groups.map((group) => (
            <section key={group.month} className={styles.month}>
              <h2 className={ui.sectionTitle}>{group.month}</h2>
              <ul className={styles.list}>
                {group.lessons.map((lesson) => (
                  <LessonRow key={lesson.id} lesson={lesson} />
                ))}
              </ul>
            </section>
          ))
        )}
      </div>

      {lessons.hasNextPage && (
        <div className={styles.more}>
          <button
            type="button"
            className={ui.button}
            disabled={lessons.isFetchingNextPage}
            onClick={() => void lessons.fetchNextPage()}
          >
            {lessons.isFetchingNextPage ? 'Loading…' : 'Load more'}
          </button>
        </div>
      )}
    </>
  );
}
