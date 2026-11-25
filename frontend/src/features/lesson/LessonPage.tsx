import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router';
import { keys } from '../../app/queries';
import { useApi } from '../../app/services';
import { Icon } from '../../components/Icon';
import { useDocumentTitle } from '../../components/useDocumentTitle';
import { Plate } from '../../components/Plate';
import { SubjectLabel } from '../../components/SubjectLabel';
import ui from '../../components/ui.module.css';
import { ApiError, type Lesson, type ReadingReport } from '../../lib/api';
import { formatMinutes, formatShortDate } from '../../lib/format';
import { FlagSheet } from './FlagSheet';
import { LessonBody } from './LessonBody';
import { LessonEnd } from './LessonEnd';
import styles from './lesson.module.css';
import { useReadingReports, useScrollProgress } from './useReading';
import { useLessonState } from './useLessonState';

export function LessonPage() {
  const { lessonId = '' } = useParams();
  const api = useApi();
  const lesson = useQuery({
    queryKey: keys.lesson(lessonId),
    queryFn: ({ signal }) => api.getLesson(lessonId, signal),
  });

  if (lesson.isPending) {
    return (
      <div className={styles.page}>
        <TopBar />
        <p className={styles.status}>Opening the lesson…</p>
      </div>
    );
  }
  if (lesson.isError) {
    const missing =
      lesson.error instanceof ApiError && lesson.error.status === 404;
    return (
      <div className={styles.page}>
        <TopBar />
        <div className={styles.status}>
          <p className={ui.notice} role="alert">
            {missing ? 'This lesson doesn’t exist.' : lesson.error.message}
          </p>
          {!missing && (
            <button
              type="button"
              className={ui.button}
              onClick={() => void lesson.refetch()}
            >
              Try again
            </button>
          )}
        </div>
      </div>
    );
  }
  return <LessonView key={lesson.data.id} lesson={lesson.data} />;
}

function useBack() {
  const navigate = useNavigate();
  const location = useLocation();
  return () => {
    // Go back when the reader was opened from inside the app; otherwise to Today.
    if (location.key !== 'default') void navigate(-1);
    else void navigate('/');
  };
}

function TopBar({
  lesson,
  onFlag,
  progress = 0,
}: {
  lesson?: Lesson;
  onFlag?: () => void;
  progress?: number;
}) {
  const back = useBack();
  const change = useLessonState(lesson?.id ?? '');
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const close = (event: Event) => {
      if (
        event instanceof KeyboardEvent
          ? event.key === 'Escape'
          : !menuRef.current?.contains(event.target as Node)
      ) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('keydown', close);
    document.addEventListener('pointerdown', close);
    return () => {
      document.removeEventListener('keydown', close);
      document.removeEventListener('pointerdown', close);
    };
  }, [menuOpen]);

  const saved = lesson?.state.saved ?? false;
  return (
    <header className={styles.topBar}>
      <div className={styles.topInner}>
        <button
          type="button"
          className={ui.iconButton}
          onClick={back}
          aria-label="Back"
        >
          <Icon name="back" />
        </button>
        {lesson && (
          <div className={styles.topActions}>
            <button
              type="button"
              className={ui.iconButton}
              aria-pressed={saved}
              aria-label={saved ? 'Saved' : 'Save'}
              onClick={() => change.mutate({ kind: 'saved', value: !saved })}
            >
              <Icon name={saved ? 'bookmarked' : 'bookmark'} />
            </button>
            <div className={styles.menu} ref={menuRef}>
              <button
                type="button"
                className={ui.iconButton}
                aria-label="More"
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                onClick={() => setMenuOpen((open) => !open)}
              >
                <Icon name="menu" />
              </button>
              {menuOpen && (
                <div className={styles.menuList} role="menu">
                  <button
                    type="button"
                    role="menuitem"
                    className={styles.menuItem}
                    onClick={() => {
                      setMenuOpen(false);
                      onFlag?.();
                    }}
                  >
                    {lesson.state.flagged
                      ? 'Flagged · add a note'
                      : 'Flag a problem'}
                  </button>
                  <Link
                    role="menuitem"
                    className={styles.menuItem}
                    to="/library"
                  >
                    Library
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      <div className={styles.progressTrack} aria-hidden="true">
        <div
          className={styles.progressLine}
          style={{ transform: `scaleX(${progress})` }}
        />
      </div>
    </header>
  );
}

function LessonView({ lesson }: { lesson: Lesson }) {
  useDocumentTitle(lesson.title);
  const api = useApi();
  const client = useQueryClient();
  const bodyRef = useRef<HTMLDivElement>(null);
  const progress = useScrollProgress(bodyRef);
  const [flagOpen, setFlagOpen] = useState(false);
  const opened = useRef(false);

  useEffect(() => {
    if (opened.current) return;
    opened.current = true;
    api
      .recordOpened(lesson.id)
      .then((state) => {
        client.setQueryData<Lesson>(keys.lesson(lesson.id), (current) =>
          current ? { ...current, state } : current,
        );
        void client.invalidateQueries({ queryKey: keys.today });
      })
      .catch(() => {
        // Recording the open is best effort; reading continues.
      });
  }, [api, client, lesson.id]);

  const send = useCallback(
    (report: ReadingReport) => api.recordReading(lesson.id, report),
    [api, lesson.id],
  );
  useReadingReports(lesson.id, bodyRef, send);

  const [first, ...rest] = lesson.illustrations;
  const total = lesson.thread.length;

  return (
    <div className={styles.page} data-subject={lesson.subject}>
      <TopBar
        lesson={lesson}
        onFlag={() => setFlagOpen(true)}
        progress={progress}
      />
      <article className={styles.article}>
        <header className={styles.header}>
          <p className={styles.kicker}>
            <SubjectLabel subject={lesson.subject} />
            {total > 1 && (
              <span className={ui.meta}>
                Part {lesson.part} of {total}
              </span>
            )}
          </p>
          <h1 className={styles.title}>{lesson.title}</h1>
          <p className={styles.hook}>{lesson.hook}</p>
          <p className={`${ui.meta} ${styles.byline}`}>
            {formatMinutes(lesson.reading_minutes)} reading ·{' '}
            {formatShortDate(lesson.local_date)}
            {lesson.request_text && <> · You asked: “{lesson.request_text}”</>}
          </p>
        </header>
        {first && (
          <Plate illustration={first} eager className={styles.frontispiece} />
        )}
        <div ref={bodyRef}>
          <LessonBody markdown={lesson.body_markdown} illustrations={rest} />
        </div>
        <LessonEnd lesson={lesson} />
      </article>
      <FlagSheet
        lesson={lesson}
        open={flagOpen}
        onClose={() => setFlagOpen(false)}
      />
    </div>
  );
}
