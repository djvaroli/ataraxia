/** A slow ink line drawing itself: the "being prepared" state. Static when motion is reduced. */
import styles from './InkLine.module.css';

export function InkLine() {
  return (
    <svg
      className={styles.line}
      viewBox="0 0 320 24"
      preserveAspectRatio="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        pathLength={1}
        d="M2 14c22-6 38-7 58-2s34 7 55 1 40-9 62-3 36 8 57 2 40-7 52-4 22 4 32 3"
      />
    </svg>
  );
}
