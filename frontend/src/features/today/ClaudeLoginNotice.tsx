/** Shown when the worker's Claude CLI is not signed in: nothing new can be prepared until it is. */
import { useRef, useState } from 'react';
import ui from '../../components/ui.module.css';
import { CLAUDE_LOGIN_COMMAND } from '../../lib/jobs';
import styles from './today.module.css';

export function ClaudeLoginNotice() {
  const [copied, setCopied] = useState(false);
  const commandRef = useRef<HTMLElement>(null);

  async function copy() {
    try {
      await navigator.clipboard.writeText(CLAUDE_LOGIN_COMMAND);
      setCopied(true);
    } catch {
      // No clipboard access (for example over plain HTTP): select the text instead.
      const node = commandRef.current;
      const selection = window.getSelection();
      if (node && selection) {
        const range = document.createRange();
        range.selectNodeContents(node);
        selection.removeAllRanges();
        selection.addRange(range);
      }
    }
  }

  return (
    <section className={styles.login} aria-labelledby="login-title">
      <h2 id="login-title" className={styles.loginTitle}>
        Lessons can’t be prepared right now
      </h2>
      <p className={styles.loginText}>
        Claude isn’t signed in on the server. On the machine running Ataraxia,
        run this and follow the link it prints:
      </p>
      <div className={styles.command}>
        <code ref={commandRef}>{CLAUDE_LOGIN_COMMAND}</code>
        <button type="button" className={ui.quiet} onClick={() => void copy()}>
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <p className={styles.loginText}>
        Lessons you already have stay readable.
      </p>
    </section>
  );
}
