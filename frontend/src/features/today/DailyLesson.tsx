/** Today's lesson in each state of the daily slot. */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router';
import { keys } from '../../app/queries';
import { useApi } from '../../app/services';
import { Icon } from '../../components/Icon';
import { InkLine } from '../../components/InkLine';
import { SubjectLabel } from '../../components/SubjectLabel';
import ui from '../../components/ui.module.css';
import type { DailySlot, LessonSummary } from '../../lib/api';
import { formatHour, formatMinutes, formatTime } from '../../lib/format';
import { deferredUntil, failureHint, failureReason } from '../../lib/jobs';
import styles from './today.module.css';

interface DailyLessonProps {
  slot: DailySlot;
  canRequest: boolean;
  timeZone: string | undefined;
  now: Date;
}

export function DailyLesson({
  slot,
  canRequest,
  timeZone,
  now,
}: DailyLessonProps) {
  const api = useApi();
  const client = useQueryClient();
  const refresh = () => client.invalidateQueries({ queryKey: keys.today });
  const start = useMutation({
    mutationFn: () => api.startDailyLesson(),
    onSettled: refresh,
  });
  const retry = useMutation({
    mutationFn: (jobId: string) => api.retryJob(jobId),
    onSettled: refresh,
  });

  if (slot.status === 'ready' && slot.lesson) {
    return <Cover lesson={slot.lesson} />;
  }

  const startButton = (
    <button
      type="button"
      className={ui.primary}
      disabled={!canRequest || start.isPending}
      onClick={() => start.mutate()}
    >
      {start.isPending ? 'Starting…' : 'Start today’s lesson'}
    </button>
  );
  const startError = start.error && (
    <p className={ui.error} role="alert">
      {start.error.message}
    </p>
  );

  if (slot.status === 'queued' || slot.status === 'running') {
    const waitUntil = slot.job ? deferredUntil(slot.job, now) : null;
    return (
      <section className={styles.slot} aria-labelledby="daily-title">
        <p className={styles.slotLabel}>Today’s lesson</p>
        <h2 id="daily-title" className={styles.slotTitle}>
          {waitUntil ? 'Waiting to be written' : 'Preparing…'}
        </h2>
        <div className={styles.ink}>
          <InkLine />
        </div>
        <p className={styles.slotText} role="status">
          {waitUntil
            ? `${slot.job ? failureReason(slot.job) : ''} It will try again at ${formatTime(waitUntil, timeZone)}.`
            : slot.status === 'running'
              ? 'Claude is writing it now. This page updates by itself.'
              : 'It is next in line. This page updates by itself.'}
        </p>
      </section>
    );
  }

  if (slot.status === 'failed' && slot.job) {
    const job = slot.job;
    const hint = failureHint(job);
    return (
      <section className={styles.slot} aria-labelledby="daily-title">
        <p className={styles.slotLabel}>Today’s lesson</p>
        <h2 id="daily-title" className={styles.slotTitle}>
          It couldn’t be prepared.
        </h2>
        <p className={styles.failure} role="alert">
          {failureReason(job)}
          {hint && <span className={styles.hint}>{hint}</span>}
        </p>
        {job.can_retry && (
          <div className={styles.actions}>
            <button
              type="button"
              className={ui.button}
              disabled={retry.isPending || !canRequest}
              onClick={() => retry.mutate(job.id)}
            >
              {retry.isPending ? 'Retrying…' : 'Retry'}
            </button>
          </div>
        )}
        {retry.error && (
          <p className={ui.error} role="alert">
            {retry.error.message}
          </p>
        )}
      </section>
    );
  }

  return (
    <section className={styles.slot} aria-labelledby="daily-title">
      <p className={styles.slotLabel}>Today’s lesson</p>
      <h2 id="daily-title" className={styles.slotTitle}>
        {slot.status === 'waiting' && slot.morning_hour !== null
          ? `Arrives at ${formatHour(slot.morning_hour)}.`
          : 'Not started yet.'}
      </h2>
      <p className={styles.slotText}>
        {slot.status === 'waiting'
          ? 'It will be prepared in the morning, or you can start it now.'
          : 'A new lesson is chosen for you when you start it.'}
      </p>
      <div className={styles.actions}>{startButton}</div>
      {startError}
    </section>
  );
}

function Cover({ lesson }: { lesson: LessonSummary }) {
  const opened = lesson.state.first_opened_at !== null;
  const finished = lesson.state.finished_at !== null;
  const href = `/lessons/${lesson.id}`;
  return (
    <article
      className={styles.cover}
      data-subject={lesson.subject}
      aria-labelledby="daily-title"
    >
      <p className={styles.coverLabel}>
        <span className={styles.slotLabelInline}>Today’s lesson</span>
        <SubjectLabel subject={lesson.subject} />
      </p>
      <h2 id="daily-title" className={styles.coverTitle}>
        <Link to={href}>{lesson.title}</Link>
      </h2>
      <p className={styles.hook}>{lesson.hook}</p>
      <div className={styles.coverFoot}>
        <Link to={href} className={ui.primary}>
          {finished
            ? 'Read again'
            : opened
              ? 'Continue reading'
              : 'Begin reading'}
          <Icon name="arrow" size={18} />
        </Link>
        <span className={ui.meta}>
          {formatMinutes(lesson.reading_minutes)}
          {lesson.part > 1 && ` · Part ${lesson.part}`}
          {finished && ' · Finished'}
        </span>
      </div>
    </article>
  );
}
