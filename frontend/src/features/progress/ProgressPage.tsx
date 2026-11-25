import { Link } from 'react-router';
import { useMe, useProgress, useSubjectLabel } from '../../app/queries';
import { Icon } from '../../components/Icon';
import { PageHeader } from '../../components/PageHeader';
import ui from '../../components/ui.module.css';
import type { DayActivity, Progress } from '../../lib/api';
import { formatShortDate, plural, weekdayIndex } from '../../lib/format';
import styles from './progress.module.css';

export function ProgressPage() {
  const progress = useProgress();
  return (
    <>
      <PageHeader title="Progress" />
      {progress.isPending ? (
        <p className={styles.loading}>Counting…</p>
      ) : progress.isError ? (
        <div className={styles.loading}>
          <p className={ui.notice} role="alert">
            {progress.error.message}
          </p>
          <button
            type="button"
            className={ui.button}
            onClick={() => void progress.refetch()}
          >
            Try again
          </button>
        </div>
      ) : (
        <ProgressView progress={progress.data} />
      )}
      <p className={styles.settings}>
        <Link to="/settings" className={ui.quiet}>
          Settings
          <Icon name="arrow" size={18} />
        </Link>
      </p>
    </>
  );
}

function ProgressView({ progress }: { progress: Progress }) {
  return (
    <>
      <section className={styles.streaks} aria-label="Streaks">
        <div className={styles.streak}>
          <span className={styles.figure}>{progress.current_streak}</span>
          <span className={styles.figureLabel}>
            {progress.current_streak === 1 ? 'day' : 'days'} in a row
          </span>
        </div>
        <div className={styles.streak}>
          <span className={styles.figure}>{progress.longest_streak}</span>
          <span className={styles.figureLabel}>longest run</span>
        </div>
      </section>

      <dl className={styles.totals}>
        <div>
          <dt>Finished</dt>
          <dd>{progress.finished_total}</dd>
        </div>
        <div>
          <dt>Minutes</dt>
          <dd>{progress.read_minutes_total}</dd>
        </div>
        <div>
          <dt>Saved</dt>
          <dd>{progress.saved_total}</dd>
        </div>
      </dl>

      <Subjects progress={progress} />
      <Calendar days={progress.days} />
    </>
  );
}

function Subjects({ progress }: { progress: Progress }) {
  const label = useSubjectLabel();
  const me = useMe();
  const enabled = me.data?.preferences.subjects;
  const most = Math.max(
    1,
    ...progress.subjects.map((subject) => subject.lessons),
  );
  return (
    <section className={styles.section} aria-labelledby="subjects-title">
      <h2 id="subjects-title" className={ui.sectionTitle}>
        By subject
      </h2>
      <ul className={styles.subjects}>
        {progress.subjects.map((subject) => {
          const off = enabled ? !enabled.includes(subject.subject) : false;
          return (
            <li key={subject.subject} data-subject={subject.subject}>
              <div className={styles.subjectHead}>
                <span className={styles.subjectName}>
                  {label(subject.subject)}
                  {off && <span className={styles.off}> · off</span>}
                </span>
                <span className={ui.meta}>
                  {subject.lessons === 0
                    ? 'None yet'
                    : `${subject.finished} of ${subject.lessons} finished · ${subject.read_minutes} min`}
                </span>
              </div>
              <div
                className={styles.bar}
                role="img"
                aria-label={`${label(subject.subject)}: ${plural(subject.lessons, 'lesson')}, ${subject.finished} finished`}
              >
                <span
                  className={styles.barAll}
                  style={{ width: `${(subject.lessons / most) * 100}%` }}
                />
                <span
                  className={styles.barFinished}
                  style={{ width: `${(subject.finished / most) * 100}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function dotSize(day: DayActivity): 0 | 1 | 2 | 3 {
  if (day.finished >= 2 || day.read_minutes >= 25) return 3;
  if (day.finished === 1) return 2;
  if (day.read_minutes > 0) return 1;
  return 0;
}

const WEEKDAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

function Calendar({ days }: { days: DayActivity[] }) {
  if (days.length === 0) return null;
  const offset = weekdayIndex(days[0].date);
  const weeks = Math.ceil((days.length + offset) / 7);
  const active = days.filter((day) => day.finished > 0).length;
  return (
    <section className={styles.section} aria-labelledby="calendar-title">
      <h2 id="calendar-title" className={ui.sectionTitle}>
        Twelve weeks
      </h2>
      <div className={styles.calendarWrap}>
        <div className={styles.weekdays} aria-hidden="true">
          {WEEKDAYS.map((day, index) => (
            <span key={index}>{index % 2 === 0 ? day : ''}</span>
          ))}
        </div>
        <ol
          className={styles.calendar}
          style={{ gridTemplateColumns: `repeat(${weeks}, 1fr)` }}
          aria-label={`${plural(active, 'day')} with a finished lesson in the last ${days.length} days`}
        >
          {days.map((day, index) => {
            const position = index + offset;
            return (
              <li
                key={day.date}
                className={styles.day}
                data-level={dotSize(day)}
                style={{
                  gridColumn: Math.floor(position / 7) + 1,
                  gridRow: (position % 7) + 1,
                }}
                title={`${formatShortDate(day.date)}: ${plural(day.finished, 'lesson')} finished, ${day.read_minutes} min`}
              >
                <span className="visually-hidden">
                  {formatShortDate(day.date)}: {plural(day.finished, 'lesson')}{' '}
                  finished
                </span>
              </li>
            );
          })}
        </ol>
      </div>
      <p className={styles.legend} aria-hidden="true">
        <span>Less</span>
        <span className={styles.day} data-level="0" />
        <span className={styles.day} data-level="1" />
        <span className={styles.day} data-level="2" />
        <span className={styles.day} data-level="3" />
        <span>More</span>
      </p>
    </section>
  );
}
