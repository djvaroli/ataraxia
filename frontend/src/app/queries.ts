/** Query keys and the shared queries several screens read. */
import { useQuery } from '@tanstack/react-query';
import { useCallback } from 'react';
import type { LessonFilters, SubjectId } from '../lib/api';
import { todayPollInterval } from '../lib/jobs';
import { useServices } from './services';

export const keys = {
  me: ['me'] as const,
  today: ['today'] as const,
  progress: ['progress'] as const,
  lessons: (filters: LessonFilters = {}) => ['lessons', filters] as const,
  lessonsAll: ['lessons'] as const,
  lesson: (id: string) => ['lesson', id] as const,
  job: (id: string) => ['job', id] as const,
};

export function useMe() {
  const { api } = useServices();
  return useQuery({
    queryKey: keys.me,
    queryFn: ({ signal }) => api.getMe(signal),
    staleTime: 5 * 60_000,
  });
}

/** Today, refreshed every few seconds while something is being prepared and the tab is visible. */
export function useToday() {
  const { api, pollMs, now } = useServices();
  return useQuery({
    queryKey: keys.today,
    queryFn: ({ signal }) => api.getToday(signal),
    refetchInterval: (query) =>
      todayPollInterval(query.state.data, now(), pollMs),
    refetchIntervalInBackground: false,
  });
}

export function useProgress() {
  const { api } = useServices();
  return useQuery({
    queryKey: keys.progress,
    queryFn: ({ signal }) => api.getProgress(signal),
  });
}

const SHORT_LABELS: Record<SubjectId, string> = {
  art: 'Art',
  history: 'History',
  film: 'Film',
  words: 'Words',
  geography: 'Geography',
  science: 'Science',
  math: 'Mathematics',
  computing: 'Computer science',
  philosophy: 'Philosophy',
  literature: 'Literature',
  music: 'Music',
};

/** Subject labels from the catalog, with a built-in fallback while it loads. */
export function useSubjectLabel(): (id: SubjectId) => string {
  const me = useMe();
  const catalog = me.data?.catalog;
  return useCallback(
    (id: SubjectId) =>
      catalog?.find((subject) => subject.id === id)?.label ?? SHORT_LABELS[id],
    [catalog],
  );
}
