import { type FormEvent, useState } from 'react';
import { Sheet } from '../../components/Sheet';
import ui from '../../components/ui.module.css';
import type { Lesson } from '../../lib/api';
import styles from './lesson.module.css';
import { useLessonState } from './useLessonState';

const NOTE_MAX = 500;

interface FlagSheetProps {
  lesson: Lesson;
  open: boolean;
  onClose: () => void;
}

export function FlagSheet({ lesson, open, onClose }: FlagSheetProps) {
  const change = useLessonState(lesson.id);
  const [note, setNote] = useState('');
  const [sent, setSent] = useState(false);

  const close = () => {
    setSent(false);
    setNote('');
    change.reset();
    onClose();
  };

  function submit(event: FormEvent) {
    event.preventDefault();
    change.mutate(
      { kind: 'flag', note: note.trim() },
      { onSuccess: () => setSent(true) },
    );
  }

  return (
    <Sheet open={open} title="Flag a problem" onClose={close}>
      {sent ? (
        <div className={styles.sheetForm}>
          <p className={styles.sheetLead} role="status">
            Thank you. The concern is recorded for later review.
          </p>
          <div>
            <button type="button" className={ui.button} onClick={close}>
              Back to the lesson
            </button>
          </div>
        </div>
      ) : (
        <form className={styles.sheetForm} onSubmit={submit}>
          <p className={styles.sheetText}>
            Something that looks wrong, misleading, or badly explained. The
            lesson stays as it is; the flag is kept with your activity record.
          </p>
          <label className={ui.field}>
            <span className={ui.fieldLabel}>
              What’s the problem? (optional)
            </span>
            <textarea
              className={ui.textarea}
              rows={3}
              maxLength={NOTE_MAX}
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
          </label>
          {change.error && (
            <p className={ui.error} role="alert">
              {change.error.message}
            </p>
          )}
          <div>
            <button
              type="submit"
              className={ui.primary}
              disabled={change.isPending}
            >
              {change.isPending ? 'Sending…' : 'Flag this lesson'}
            </button>
          </div>
        </form>
      )}
    </Sheet>
  );
}
