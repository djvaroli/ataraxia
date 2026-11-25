import { useMutation, useQueryClient } from '@tanstack/react-query';
import { lazy, Suspense, useEffect, useRef } from 'react';
import { Route, Routes } from 'react-router';
import { LibraryPage } from '../features/library/LibraryPage';
import { ProgressPage } from '../features/progress/ProgressPage';
import { SettingsPage } from '../features/settings/SettingsPage';
import { TodayPage } from '../features/today/TodayPage';
import { NotFound } from './NotFound';
import { keys, useMe } from './queries';
import { useApi } from './services';
import { Shell } from './Shell';

// The reader carries Markdown, math, and KaTeX's fonts; load it on first use.
const LessonPage = lazy(() =>
  import('../features/lesson/LessonPage').then((module) => ({
    default: module.LessonPage,
  })),
);

export function AppRoutes() {
  useAppOpened();
  useConfirmTimeZone();
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<TodayPage />} />
        <Route path="library" element={<LibraryPage />} />
        <Route path="progress" element={<ProgressPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
      <Route
        path="lessons/:lessonId"
        element={
          <Suspense fallback={null}>
            <LessonPage />
          </Suspense>
        }
      />
    </Routes>
  );
}

/** Records one `app.opened` event per load of the signed-in app. */
function useAppOpened() {
  const api = useApi();
  const sent = useRef(false);
  useEffect(() => {
    if (sent.current) return;
    sent.current = true;
    api.recordAppOpened().catch(() => {
      // Best effort: a missed open event is not worth interrupting the reader.
    });
  }, [api]);
}

/** On first run, set the owner's time zone from the browser. */
function useConfirmTimeZone() {
  const api = useApi();
  const client = useQueryClient();
  const me = useMe();
  const tried = useRef(false);
  const confirm = useMutation({
    mutationFn: (timeZone: string) => api.updateMe({ time_zone: timeZone }),
    onSuccess: (updated) => {
      client.setQueryData(keys.me, updated);
      void client.invalidateQueries({ queryKey: keys.today });
    },
  });
  const { mutate } = confirm;
  const unconfirmed = me.data?.preferences.time_zone_confirmed === false;

  useEffect(() => {
    if (!unconfirmed || tried.current) return;
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (!zone) return;
    tried.current = true;
    mutate(zone);
  }, [unconfirmed, mutate]);
}
