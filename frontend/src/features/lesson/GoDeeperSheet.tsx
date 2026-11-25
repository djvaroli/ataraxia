/** Confirm a follow-up, then watch it being prepared. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { keys, useToday } from '../../app/queries';
import { useServices } from '../../app/services';
import { InkLine } from '../../components/InkLine';
import { Sheet } from '../../components/Sheet';
import ui from '../../components/ui.module.css';
import type { Job, Lesson } from '../../lib/api';
import { failureReason, isActive, requestBlock } from '../../lib/jobs';
import styles from './lesson.module.css';

export type FollowUpChoice =
  { kind: 'direction'; index: number } | { kind: 'question' };

const QUESTION_MIN = 2;
const QUESTION_MAX = 500;

interface GoDeeperSheetProps {
  lesson: Lesson;
  choice: FollowUpChoice | null;
  onClose: () => void;
}

export function GoDeeperSheet({ lesson, choice, onClose }: GoDeeperSheetProps) {
  const [job, setJob] = useState<Job | null>(null);
  const close = () => {
    setJob(null);
    onClose();
  };
  return (
    <Sheet open={choice !== null} title="Go deeper" onClose={close}>
      {job ? (
        <FollowUpProgress job={job} part={lesson.part + 1} onClose={close} />
      ) : (
        choice && (
          <FollowUpForm lesson={lesson} choice={choice} onRequested={setJob} />
        )
      )}
    </Sheet>
  );
}

function FollowUpForm({
  lesson,
  choice,
  onRequested,
}: {
  lesson: Lesson;
  choice: FollowUpChoice;
  onRequested: (job: Job) => void;
}) {
  const { api } = useServices();
  const client = useQueryClient();
  const today = useToday();
  const [question, setQuestion] = useState('');
  const request = useMutation({
    mutationFn: () =>
      api.requestFollowUp(
        lesson.id,
        choice.kind === 'direction'
          ? { direction: choice.index }
          : { question: question.trim() },
      ),
    onSuccess: (job) => {
      client.setQueryData(keys.job(job.id), job);
      void client.invalidateQueries({ queryKey: keys.today });
      onRequested(job);
    },
  });

  const blocked = today.data ? requestBlock(today.data.allowance) : null;
  const trimmed = question.trim();
  const valid =
    choice.kind === 'direction' ||
    (trimmed.length >= QUESTION_MIN && trimmed.length <= QUESTION_MAX);
  const direction =
    choice.kind === 'direction' ? lesson.go_deeper[choice.index] : null;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (valid && !blocked) request.mutate();
  }

  return (
    <form className={styles.sheetForm} onSubmit={submit}>
      {direction ? (
        <div>
          <p className={styles.sheetLead}>{direction.title}</p>
          <p className={styles.sheetText}>{direction.description}</p>
        </div>
      ) : (
        <label className={ui.field}>
          <span className={ui.fieldLabel}>Your question</span>
          <textarea
            className={ui.textarea}
            rows={3}
            maxLength={QUESTION_MAX}
            autoFocus
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What would you like the next part to explain?"
          />
        </label>
      )}
      <p className={styles.sheetText}>
        This becomes part {lesson.part + 1} of the thread, written to follow on
        from this lesson.
      </p>
      {blocked && <p className={ui.notice}>{blocked}</p>}
      {request.error && (
        <p className={ui.error} role="alert">
          {request.error.message}
        </p>
      )}
      <div>
        <button
          type="submit"
          className={ui.primary}
          disabled={!valid || blocked !== null || request.isPending}
        >
          {request.isPending
            ? 'Requesting…'
            : `Prepare part ${lesson.part + 1}`}
        </button>
      </div>
    </form>
  );
}

function FollowUpProgress({
  job: initial,
  part,
  onClose,
}: {
  job: Job;
  part: number;
  onClose: () => void;
}) {
  const { api, pollMs } = useServices();
  const navigate = useNavigate();
  const job = useQuery({
    queryKey: keys.job(initial.id),
    queryFn: ({ signal }) => api.getJob(initial.id, signal),
    initialData: initial,
    refetchInterval: (query) =>
      query.state.data && isActive(query.state.data) ? pollMs : false,
  });
  const current = job.data;

  if (current.status === 'succeeded' && current.lesson_id) {
    const lessonId = current.lesson_id;
    return (
      <div className={styles.sheetForm}>
        <p className={styles.sheetLead} role="status">
          Part {part} is ready.
        </p>
        <div className={styles.sheetActions}>
          <button
            type="button"
            className={ui.primary}
            onClick={() => {
              onClose();
              void navigate(`/lessons/${lessonId}`);
            }}
          >
            Open part {part}
          </button>
        </div>
      </div>
    );
  }
  if (current.status === 'failed') {
    return (
      <div className={styles.sheetForm}>
        <p className={styles.sheetLead}>Part {part} couldn’t be prepared.</p>
        <p className={styles.sheetText} role="alert">
          {failureReason(current)} You can retry it from Today.
        </p>
        <div className={styles.sheetActions}>
          <Link className={ui.button} to="/" onClick={onClose}>
            Go to Today
          </Link>
        </div>
      </div>
    );
  }
  return (
    <div className={styles.sheetForm}>
      <p className={styles.sheetLead}>Preparing part {part}…</p>
      <InkLine />
      <p className={styles.sheetText} role="status">
        This usually takes a minute or two. You can keep reading; it will also
        be on Today when it’s ready.
      </p>
      <div className={styles.sheetActions}>
        <button type="button" className={ui.button} onClick={onClose}>
          Keep reading
        </button>
        <Link className={ui.quiet} to="/" onClick={onClose}>
          Go to Today
        </Link>
      </div>
    </div>
  );
}
