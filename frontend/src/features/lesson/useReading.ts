/**
 * Reading measurement for one visit to the reader: how far down the text the
 * reader has been, and how long the page was visible. Reports are cumulative
 * and the server keeps the largest values per session, so a repeated or lost
 * report is harmless.
 */
import { type RefObject, useEffect, useState } from 'react';
import type { ReadingReport } from '../../lib/api';

export const REPORT_INTERVAL_MS = 30_000;
const MAX_SECONDS = 14_400;

/** A random UUID; `randomUUID` needs a secure context, `getRandomValues` does not. */
export function newSessionId(): string {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0'));
  return [
    hex.slice(0, 4),
    hex.slice(4, 6),
    hex.slice(6, 8),
    hex.slice(8, 10),
    hex.slice(10),
  ]
    .map((group) => group.join(''))
    .join('-');
}

/** The fraction (0–1) of `element` that has passed the bottom of the viewport. */
export function readFraction(element: HTMLElement | null): number {
  if (!element) return 0;
  const rect = element.getBoundingClientRect();
  if (rect.height <= 0) return 0;
  const seen = window.innerHeight - rect.top;
  return Math.min(1, Math.max(0, seen / rect.height));
}

/** The current read fraction, updated once per animation frame while scrolling. */
export function useScrollProgress(ref: RefObject<HTMLElement | null>): number {
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      setProgress(readFraction(ref.current));
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    schedule();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    return () => {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
    };
  }, [ref]);
  return progress;
}

/**
 * Sends a reading report every 30 seconds while the page is visible, when it
 * is hidden, and when the reader closes. Each mount is a new session.
 */
export function useReadingReports(
  lessonId: string,
  ref: RefObject<HTMLElement | null>,
  send: (report: ReadingReport) => Promise<void>,
): void {
  useEffect(() => {
    const sessionId = newSessionId();
    let seconds = 0;
    let visibleSince: number | null =
      document.visibilityState === 'visible' ? Date.now() : null;
    let furthest = readFraction(ref.current);
    let last = { seconds: 0, scroll: 0 };

    const elapsed = () =>
      seconds +
      (visibleSince === null ? 0 : (Date.now() - visibleSince) / 1000);

    const report = () => {
      const current = {
        seconds: Math.min(MAX_SECONDS, Math.floor(elapsed())),
        scroll: Math.round(furthest * 1000) / 1000,
      };
      if (current.seconds === last.seconds && current.scroll === last.scroll) {
        return;
      }
      last = current;
      send({ session_id: sessionId, ...current }).catch(() => {
        // A lost report costs at most one interval; the next one repeats the totals.
      });
    };

    const onScroll = () => {
      furthest = Math.max(furthest, readFraction(ref.current));
    };
    const onVisibility = () => {
      if (document.visibilityState === 'hidden') {
        seconds = elapsed();
        visibleSince = null;
        report();
      } else if (visibleSince === null) {
        visibleSince = Date.now();
      }
    };
    const timer = window.setInterval(() => {
      if (visibleSince !== null) report();
    }, REPORT_INTERVAL_MS);

    window.addEventListener('scroll', onScroll, { passive: true });
    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('pagehide', report);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('scroll', onScroll);
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('pagehide', report);
      onScroll();
      report();
    };
  }, [lessonId, ref, send]);
}
