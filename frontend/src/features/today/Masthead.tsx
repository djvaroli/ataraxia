import { formatDateline } from '../../lib/format';
import styles from './today.module.css';

interface MastheadProps {
  localDate: string;
  /** Lessons prepared so far; shown as the issue number. */
  issue: number | null;
}

export function Masthead({ localDate, issue }: MastheadProps) {
  const [weekday, rest] = formatDateline(localDate).split(', ');
  return (
    <header className={styles.masthead}>
      <p className={styles.mastheadTop}>
        <span>Ataraxia</span>
        {issue !== null && issue > 0 && (
          <span className={styles.issue}>No. {issue}</span>
        )}
      </p>
      <h1 className={styles.dateline}>
        <span className={styles.weekday}>{weekday},</span> {rest}
      </h1>
    </header>
  );
}
