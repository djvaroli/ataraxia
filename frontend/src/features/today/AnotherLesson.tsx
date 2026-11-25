/** "Another lesson": surprise, a chosen subject, or any topic. */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useState } from 'react';
import { keys } from '../../app/queries';
import { useApi } from '../../app/services';
import ui from '../../components/ui.module.css';
import type { Allowance, LessonRequest, SubjectInfo } from '../../lib/api';
import { plural } from '../../lib/format';
import { requestBlock } from '../../lib/jobs';
import styles from './today.module.css';

const TOPIC_MIN = 2;
const TOPIC_MAX = 300;

interface AnotherLessonProps {
  allowance: Allowance;
  subjects: SubjectInfo[];
}

export function AnotherLesson({ allowance, subjects }: AnotherLessonProps) {
  const api = useApi();
  const client = useQueryClient();
  const [topic, setTopic] = useState('');
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const request = useMutation({
    mutationFn: (body: LessonRequest) => api.requestLesson(body),
    onSuccess: (_job, body) => {
      if (body.kind === 'topic') setTopic('');
      setConfirmation('Requested. It will appear here when it’s ready.');
    },
    onSettled: () => client.invalidateQueries({ queryKey: keys.today }),
  });

  const blocked = requestBlock(allowance);
  const disabled = blocked !== null || request.isPending;
  const trimmed = topic.trim();
  const topicValid = trimmed.length >= TOPIC_MIN && trimmed.length <= TOPIC_MAX;

  function send(body: LessonRequest) {
    setConfirmation(null);
    request.mutate(body);
  }

  function submitTopic(event: FormEvent) {
    event.preventDefault();
    if (topicValid && !disabled) send({ kind: 'topic', topic: trimmed });
  }

  return (
    <section className={styles.section} aria-labelledby="another-title">
      <h2 id="another-title" className={ui.sectionTitle}>
        Another lesson
      </h2>

      {blocked ? (
        <p className={ui.notice}>{blocked}</p>
      ) : (
        allowance.remaining <= 2 && (
          <p className={ui.notice}>
            {plural(allowance.remaining, 'lesson')} left today.
          </p>
        )
      )}

      <div className={styles.surprise}>
        <button
          type="button"
          className={ui.button}
          disabled={disabled}
          onClick={() => send({ kind: 'surprise' })}
        >
          Surprise me
        </button>
        <span className={styles.surpriseNote}>
          A subject and topic chosen for you.
        </span>
      </div>

      <h3 className={styles.subhead}>Or choose a subject</h3>
      <ul className={styles.subjects}>
        {subjects.map((subject) => (
          <li key={subject.id} data-subject={subject.id}>
            <button
              type="button"
              className={styles.subjectButton}
              disabled={disabled}
              onClick={() => send({ kind: 'subject', subject: subject.id })}
              title={subject.description}
            >
              {subject.label}
            </button>
          </li>
        ))}
      </ul>

      <form className={styles.topicForm} onSubmit={submitTopic}>
        <label className={ui.field}>
          <span className={styles.subhead}>Or ask about anything</span>
          <textarea
            className={ui.textarea}
            rows={2}
            maxLength={TOPIC_MAX}
            placeholder="The history of the semicolon, how bridges stand up…"
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
          />
        </label>
        <div className={styles.topicFoot}>
          <span className={ui.meta} aria-live="polite">
            {trimmed.length > TOPIC_MAX - 40
              ? `${TOPIC_MAX - trimmed.length} characters left`
              : ''}
          </span>
          <button
            type="submit"
            className={ui.button}
            disabled={disabled || !topicValid}
          >
            Ask
          </button>
        </div>
      </form>

      <div aria-live="polite">
        {request.error ? (
          <p className={ui.error} role="alert">
            {request.error.message}
          </p>
        ) : (
          confirmation && <p className={styles.confirm}>{confirmation}</p>
        )}
      </div>
    </section>
  );
}
