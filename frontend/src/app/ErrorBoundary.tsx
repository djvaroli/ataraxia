/**
 * Catches render errors and failed page loads (for example, a reader chunk
 * that no longer exists after a redeploy while the installed app stayed open)
 * so the app offers a reload instead of going blank.
 */
import { Component, type ReactNode } from 'react';
import ui from '../components/ui.module.css';
import styles from '../features/auth/auth.module.css';

interface ErrorBoundaryProps {
  children: ReactNode;
}

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className={styles.page}>
        <p className={styles.wordmark}>Ataraxia</p>
        <h1 className={styles.headline}>This page couldn’t be shown.</h1>
        <p className={styles.quiet}>
          Reloading usually fixes it, for example after Ataraxia was updated.
        </p>
        <div>
          <button
            type="button"
            className={ui.primary}
            onClick={() => window.location.reload()}
          >
            Reload
          </button>
        </div>
      </main>
    );
  }
}
