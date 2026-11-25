/** One lesson in a list: subject, title, minutes, and its marks. */
import { Link } from 'react-router';
import type { LessonSummary } from '../lib/api';
import { formatMinutes } from '../lib/format';
import { Icon } from './Icon';
import styles from './LessonRow.module.css';
import { SubjectLabel } from './SubjectLabel';
import ui from './ui.module.css';

interface LessonRowProps {
  lesson: LessonSummary;
  /** Show how far it has been read, for "Continue reading". */
  showProgress?: boolean;
}

export function LessonRow({ lesson, showProgress = false }: LessonRowProps) {
  const finished = lesson.state.finished_at !== null;
  const progress = Math.round(lesson.state.furthest_scroll * 100);
  return (
    <li className={styles.row} data-subject={lesson.subject}>
      <Link to={`/lessons/${lesson.id}`} className={styles.link}>
        <span className={styles.top}>
          <SubjectLabel subject={lesson.subject} />
          {lesson.part > 1 && (
            <span className={ui.meta}>Part {lesson.part}</span>
          )}
        </span>
        <span className={styles.title}>{lesson.title}</span>
        <span className={`${ui.meta} ${styles.bottom}`}>
          <span>{formatMinutes(lesson.reading_minutes)}</span>
          {finished && (
            <span className={styles.mark}>
              <Icon name="check" size={15} />
              Finished
            </span>
          )}
          {lesson.state.saved && (
            <span className={styles.mark}>
              <Icon name="bookmarked" size={13} />
              Saved
            </span>
          )}
          {showProgress && !finished && (
            <span>{progress > 0 ? `${progress}% read` : 'Opened'}</span>
          )}
        </span>
        {showProgress && !finished && (
          <span className={styles.progress} aria-hidden="true">
            <span style={{ width: `${Math.max(progress, 2)}%` }} />
          </span>
        )}
      </Link>
    </li>
  );
}
