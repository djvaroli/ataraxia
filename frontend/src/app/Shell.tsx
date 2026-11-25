/** The frame around Today, Library, Progress, and Settings: a column and the bottom navigation. */
import { useEffect } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router';
import styles from './Shell.module.css';

const SECTIONS = [
  { to: '/', label: 'Today', end: true },
  { to: '/library', label: 'Library', end: false },
  { to: '/progress', label: 'Progress', end: false },
] as const;

export function Shell() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div className={styles.frame}>
      <a className={styles.skip} href="#main">
        Skip to content
      </a>
      <main id="main" className={styles.main} tabIndex={-1}>
        <div key={pathname} className={styles.page}>
          <Outlet />
        </div>
      </main>
      <nav className={styles.nav} aria-label="Sections">
        <ul className={styles.navList}>
          {SECTIONS.map((section) => (
            <li key={section.to}>
              <NavLink
                to={section.to}
                end={section.end}
                className={({ isActive }) =>
                  isActive ||
                  (section.to === '/progress' && pathname === '/settings')
                    ? `${styles.navLink} ${styles.active}`
                    : styles.navLink
                }
              >
                {section.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
