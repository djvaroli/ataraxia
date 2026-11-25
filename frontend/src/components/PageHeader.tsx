import type { ReactNode } from 'react';
import styles from './PageHeader.module.css';
import { useDocumentTitle } from './useDocumentTitle';

interface PageHeaderProps {
  title: string;
  kicker?: string;
  children?: ReactNode;
}

export function PageHeader({ title, kicker, children }: PageHeaderProps) {
  useDocumentTitle(title);
  return (
    <header className={styles.header}>
      <p className={styles.kicker}>{kicker ?? 'Ataraxia'}</p>
      <h1 className={styles.title}>{title}</h1>
      {children}
    </header>
  );
}
