import { useQuery } from '@tanstack/react-query';
import { getReadiness } from '../lib/api';
import styles from './App.module.css';

export function App() {
  const health = useQuery({
    queryKey: ['readiness'],
    queryFn: ({ signal }) => getReadiness(signal),
  });

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <a href="/" className={styles.wordmark} aria-label="Ataraxia home">
          <span aria-hidden="true" className={styles.mark}>
            a
          </span>
          Ataraxia
        </a>
        <span className={styles.tag}>A daily practice</span>
      </header>
      <main className={styles.main}>
        <p className={styles.eyebrow}>Make a little room</p>
        <h1>
          A little progress.
          <br />
          Something to discover.
        </h1>
        <p className={styles.intro}>
          A quiet place to build habits, follow your curiosity, and return to
          what matters.
        </p>
        <section className={styles.card} aria-labelledby="welcome-title">
          <span aria-hidden="true" className={styles.circle} />
          <div>
            <h2 id="welcome-title">A beginning</h2>
            <p>Habit tracking and daily discoveries are coming next.</p>
            <p role="status" className={styles.status}>
              {health.isPending
                ? 'Connecting…'
                : health.isError
                  ? 'We couldn’t connect. Please try again.'
                  : 'Connected. There’s room to grow.'}
            </p>
            {health.isError && (
              <button
                onClick={() => void health.refetch()}
                disabled={health.isFetching}
              >
                {health.isFetching ? 'Connecting…' : 'Try again'}
              </button>
            )}
          </div>
        </section>
      </main>
      <footer className={styles.footer}>Small steps, made your own.</footer>
    </div>
  );
}
