/** The end matter: what to remember, glossary, further, go deeper, thread, and the reader's marks. */
import { useState } from 'react';
import { Link } from 'react-router';
import { Icon } from '../../components/Icon';
import ui from '../../components/ui.module.css';
import type { FurtherItem, Lesson, Rating } from '../../lib/api';
import { wikipediaSearchUrl } from '../../lib/links';
import { GoDeeperSheet, type FollowUpChoice } from './GoDeeperSheet';
import styles from './lesson.module.css';
import { useLessonState } from './useLessonState';

const KIND_LABEL: Record<FurtherItem['kind'], string> = {
  book: 'Book',
  film: 'Film',
  artwork: 'Artwork',
  music: 'Music',
  place: 'Place',
  article: 'Article',
  other: 'Other',
};

export function LessonEnd({ lesson }: { lesson: Lesson }) {
  const change = useLessonState(lesson.id);
  const [choice, setChoice] = useState<FollowUpChoice | null>(null);
  const { state } = lesson;
  const finished = state.finished_at !== null;

  const rate = (value: Exclude<Rating, 0>) =>
    change.mutate({
      kind: 'rating',
      value: state.rating === value ? 0 : value,
    });

  return (
    <footer className={styles.end}>
      <p className={styles.fin} aria-hidden="true">
        ❧
      </p>

      <section className={styles.endSection} aria-labelledby="remember-title">
        <h2 id="remember-title" className={ui.sectionTitle}>
          What to remember
        </h2>
        <ol className={styles.remember}>
          {lesson.key_ideas.map((idea) => (
            <li key={idea}>{idea}</li>
          ))}
        </ol>
      </section>

      {lesson.glossary.length > 0 && (
        <section className={styles.endSection} aria-labelledby="glossary-title">
          <h2 id="glossary-title" className={ui.sectionTitle}>
            Glossary
          </h2>
          <dl className={styles.glossary}>
            {lesson.glossary.map((entry) => (
              <div key={entry.term}>
                <dt>{entry.term}</dt>
                <dd>{entry.definition}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {lesson.further.length > 0 && (
        <section className={styles.endSection} aria-labelledby="further-title">
          <h2 id="further-title" className={ui.sectionTitle}>
            Further
          </h2>
          <ul className={styles.further}>
            {lesson.further.map((item) => (
              <li key={`${item.title}-${item.creator ?? ''}`}>
                <span className={ui.meta}>{KIND_LABEL[item.kind]}</span>
                <a
                  href={wikipediaSearchUrl(item)}
                  target="_blank"
                  rel="noreferrer noopener"
                  className={styles.furtherLink}
                >
                  <cite>{item.title}</cite>
                  {item.creator && (
                    <span className={styles.creator}> · {item.creator}</span>
                  )}
                </a>
                {item.note && <p className={styles.furtherNote}>{item.note}</p>}
              </li>
            ))}
          </ul>
          <p className={`${ui.meta} ${styles.furtherSource}`}>
            Links open a Wikipedia search.
          </p>
        </section>
      )}

      <section className={styles.endSection} aria-labelledby="marks-title">
        <h2 id="marks-title" className="visually-hidden">
          Your marks
        </h2>
        <div className={styles.marks}>
          <button
            type="button"
            className={finished ? ui.button : ui.primary}
            aria-pressed={finished}
            onClick={() =>
              change.mutate({ kind: 'finished', value: !finished })
            }
          >
            {finished && <Icon name="check" size={18} />}
            {finished ? 'Finished' : 'Mark as finished'}
          </button>
          <button
            type="button"
            className={ui.quiet}
            aria-pressed={state.saved}
            onClick={() =>
              change.mutate({ kind: 'saved', value: !state.saved })
            }
          >
            <Icon name={state.saved ? 'bookmarked' : 'bookmark'} size={18} />
            {state.saved ? 'Saved' : 'Save'}
          </button>
        </div>
        <div className={styles.rating} role="group" aria-label="Rating">
          <button
            type="button"
            className={styles.rateButton}
            aria-pressed={state.rating === 1}
            onClick={() => rate(1)}
          >
            More like this
          </button>
          <span aria-hidden="true" className={styles.rateRule} />
          <button
            type="button"
            className={styles.rateButton}
            aria-pressed={state.rating === -1}
            onClick={() => rate(-1)}
          >
            Less like this
          </button>
        </div>
        {change.error && (
          <p className={ui.error} role="alert">
            {change.error.message}
          </p>
        )}
      </section>

      <section className={styles.endSection} aria-labelledby="deeper-title">
        <h2 id="deeper-title" className={ui.sectionTitle}>
          Go deeper
        </h2>
        <ul className={styles.directions}>
          {lesson.go_deeper.map((direction, index) => (
            <li key={direction.title}>
              <button
                type="button"
                className={styles.direction}
                onClick={() => setChoice({ kind: 'direction', index })}
              >
                <span className={styles.directionTitle}>{direction.title}</span>
                <span className={styles.directionText}>
                  {direction.description}
                </span>
              </button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          className={ui.quiet}
          onClick={() => setChoice({ kind: 'question' })}
        >
          Ask your own question
          <Icon name="arrow" size={18} />
        </button>
      </section>

      {lesson.thread.length > 1 && (
        <nav className={styles.endSection} aria-labelledby="thread-title">
          <h2 id="thread-title" className={ui.sectionTitle}>
            This thread
          </h2>
          <ol className={styles.thread}>
            {lesson.thread.map((entry) => (
              <li key={entry.id}>
                <span className={styles.threadPart}>{entry.part}</span>
                {entry.id === lesson.id ? (
                  <span aria-current="page" className={styles.threadCurrent}>
                    {entry.title}
                  </span>
                ) : (
                  <Link to={`/lessons/${entry.id}`}>{entry.title}</Link>
                )}
              </li>
            ))}
          </ol>
        </nav>
      )}

      <GoDeeperSheet
        lesson={lesson}
        choice={choice}
        onClose={() => setChoice(null)}
      />
    </footer>
  );
}
