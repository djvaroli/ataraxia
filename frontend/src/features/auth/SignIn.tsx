import { type FormEvent, useState } from 'react';
import type { AuthClient } from '../../lib/auth';
import { SignInError } from '../../lib/auth';
import ui from '../../components/ui.module.css';
import styles from './auth.module.css';

interface SignInProps {
  auth: AuthClient;
  notice: string | null;
}

export function SignIn({ auth, notice }: SignInProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await auth.signIn(email.trim(), password);
    } catch (caught) {
      setError(
        caught instanceof SignInError
          ? caught.message
          : 'Sign-in failed. Try again.',
      );
      setPending(false);
    }
  }

  return (
    <main className={styles.page}>
      <p className={styles.wordmark}>Ataraxia</p>
      <h1 className={styles.headline}>A lesson a day, read slowly.</h1>
      {notice && (
        <p className={ui.notice} role="status">
          {notice}
        </p>
      )}
      <form className={styles.form} onSubmit={submit} noValidate>
        <label className={ui.field}>
          <span className={ui.fieldLabel}>Email</span>
          <input
            className={ui.input}
            type="email"
            name="email"
            autoComplete="username"
            inputMode="email"
            autoCapitalize="none"
            spellCheck={false}
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label className={ui.field}>
          <span className={ui.fieldLabel}>Password</span>
          <input
            className={ui.input}
            type="password"
            name="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error && (
          <p className={ui.error} role="alert">
            {error}
          </p>
        )}
        <button
          className={ui.primary}
          type="submit"
          disabled={pending || !email.trim() || !password}
        >
          {pending ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      <p className={styles.footnote}>
        Only the owner’s account can sign in. It is created in the Firebase
        console; there is no sign-up here.
      </p>
    </main>
  );
}
