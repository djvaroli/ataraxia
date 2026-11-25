import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { keys, useMe, useProgress, useToday } from '../../app/queries';
import { useServices } from '../../app/services';
import { LessonRow } from '../../components/LessonRow';
import { useDocumentTitle } from '../../components/useDocumentTitle';
import ui from '../../components/ui.module.css';
import type { Today } from '../../lib/api';
import { formatDay } from '../../lib/format';
import { isActive, requestBlock } from '../../lib/jobs';
import { AnotherLesson } from './AnotherLesson';
import { DailyLesson } from './DailyLesson';
import { JobList } from './JobList';
import { Masthead } from './Masthead';
import styles from './today.module.css';

const LOGIN_WARNING_DAYS = 7;
const RECENT = { limit: 10 } as const;

export function TodayPage() {
  useDocumentTitle('Today');
  const { now } = useServices();
  const today = useToday();
  const me = useMe();
  const progress = useProgress();

  if (today.isPending) {
    return <p className={styles.loading}>Opening today…</p>;
  }
  if (today.isError) {
    return (
      <div className={styles.loadError}>
        <p className={ui.notice} role="alert">
          {today.error.message}
        </p>
        <button
          type="button"
          className={ui.button}
          onClick={() => void today.refetch()}
        >
          Try again
        </button>
      </div>
    );
  }

  const data = today.data;
  const timeZone = me.data?.preferences.time_zone;
  const enabled = me.data
    ? me.data.catalog.filter((subject) =>
        me.data.preferences.subjects.includes(subject.id),
      )
    : [];
  const canRequest = requestBlock(data.allowance) === null;
  const current = now();

  return (
    <>
      <Masthead
        localDate={data.local_date}
        issue={progress.data?.lessons_total ?? null}
      />
      <Notices today={data} timeZone={timeZone} now={current} />
      <DailyLesson
        slot={data.daily}
        canRequest={canRequest}
        timeZone={timeZone}
        now={current}
      />
      <JobList
        jobs={data.jobs}
        canRequest={canRequest}
        timeZone={timeZone}
        now={current}
      />
      <ReadyToday today={data} />
      {data.unfinished.length > 0 && (
        <section className={styles.section} aria-labelledby="continue-title">
          <h2 id="continue-title" className={ui.sectionTitle}>
            Continue reading
          </h2>
          <ul className={styles.list}>
            {data.unfinished.map((lesson) => (
              <LessonRow key={lesson.id} lesson={lesson} showProgress />
            ))}
          </ul>
        </section>
      )}
      <AnotherLesson allowance={data.allowance} subjects={enabled} />
    </>
  );
}

/**
 * Lessons prepared today, other than the daily one, that have not been opened.
 * Today's response does not list them, so they come from the newest lessons.
 */
function ReadyToday({ today }: { today: Today }) {
  const { api } = useServices();
  const client = useQueryClient();
  const recent = useQuery({
    queryKey: keys.lessons(RECENT),
    queryFn: ({ signal }) => api.listLessons(RECENT, signal),
  });
  const active = today.jobs.filter(isActive).length;
  const previous = useRef(active);

  useEffect(() => {
    // A job finished: its lesson is now in the list.
    if (active < previous.current) {
      void client.invalidateQueries({ queryKey: keys.lessonsAll });
      void client.invalidateQueries({ queryKey: keys.progress });
    }
    previous.current = active;
  }, [active, client]);

  const dailyId = today.daily.lesson?.id;
  const fresh = (recent.data?.items ?? []).filter(
    (lesson) =>
      lesson.local_date === today.local_date &&
      lesson.id !== dailyId &&
      lesson.state.first_opened_at === null,
  );
  if (fresh.length === 0) return null;
  return (
    <section className={styles.section} aria-labelledby="fresh-title">
      <h2 id="fresh-title" className={ui.sectionTitle}>
        Also ready today
      </h2>
      <ul className={styles.list}>
        {fresh.map((lesson) => (
          <LessonRow key={lesson.id} lesson={lesson} />
        ))}
      </ul>
    </section>
  );
}

function Notices({
  today,
  timeZone,
  now,
}: {
  today: Today;
  timeZone: string | undefined;
  now: Date;
}) {
  const notes: string[] = [];
  const { worker } = today;
  if (!worker.online) {
    notes.push(
      'The lesson worker isn’t running, so nothing new will be prepared until it starts again.',
    );
  }
  if (worker.login_expires_at) {
    const ends = new Date(worker.login_expires_at);
    const days = (ends.getTime() - now.getTime()) / 86_400_000;
    if (days <= 0) {
      notes.push(
        'Claude’s login on the server has expired. Sign it in again to prepare lessons.',
      );
    } else if (days <= LOGIN_WARNING_DAYS) {
      notes.push(
        `Claude’s login on the server ends on ${formatDay(worker.login_expires_at, timeZone)}. Renew it before then.`,
      );
    }
  }
  if (notes.length === 0) return null;
  return (
    <div className={styles.notices}>
      {notes.map((note) => (
        <p key={note} className={ui.notice} role="status">
          {note}
        </p>
      ))}
    </div>
  );
}
