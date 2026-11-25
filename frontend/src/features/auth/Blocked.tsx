/** Full-page states before the app can run: loading, unreachable, wrong account. */
import ui from '../../components/ui.module.css';
import styles from './auth.module.css';

export function Opening() {
  return (
    <main className={styles.page} aria-busy="true">
      <p className={styles.wordmark}>Ataraxia</p>
      <p className={styles.quiet} role="status">
        Opening…
      </p>
    </main>
  );
}

interface UnavailableProps {
  message: string;
  onRetry: () => void;
}

export function Unavailable({ message, onRetry }: UnavailableProps) {
  return (
    <main className={styles.page}>
      <p className={styles.wordmark}>Ataraxia</p>
      <h1 className={styles.headline}>The reading room is closed for now.</h1>
      <p className={ui.notice} role="alert">
        {message}
      </p>
      <div>
        <button type="button" className={ui.button} onClick={onRetry}>
          Try again
        </button>
      </div>
    </main>
  );
}

interface ForbiddenProps {
  mode: 'firebase' | 'local';
  onSignOut: () => void;
}

export function Forbidden({ mode, onSignOut }: ForbiddenProps) {
  return (
    <main className={styles.page}>
      <p className={styles.wordmark}>Ataraxia</p>
      <h1 className={styles.headline}>This account isn’t the owner.</h1>
      {mode === 'firebase' ? (
        <>
          <p className={styles.quiet}>
            Ataraxia belongs to one person. Sign out and sign in with the
            owner’s account.
          </p>
          <div>
            <button type="button" className={ui.button} onClick={onSignOut}>
              Sign out
            </button>
          </div>
        </>
      ) : (
        <p className={styles.quiet}>
          Local mode only answers requests made to localhost on the machine
          running Ataraxia. Open it there, or set up Firebase sign-in.
        </p>
      )}
    </main>
  );
}
