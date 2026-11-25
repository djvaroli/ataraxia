/**
 * Every outbound link and image in a lesson is checked or built here, so model
 * output can never choose a destination.
 */
import type { FurtherItem } from './api';

const IMAGE_HOSTS = new Set(['upload.wikimedia.org', 'thumb.wikimedia.org']);

/** A Wikipedia search for a book, film, work, or place. */
export function wikipediaSearchUrl(
  item: Pick<FurtherItem, 'title' | 'creator'>,
) {
  const terms = [item.title, item.creator].filter(Boolean).join(' ');
  return `https://en.wikipedia.org/w/index.php?search=${encodeURIComponent(terms)}`;
}

function parse(url: string): URL | null {
  try {
    return new URL(url);
  } catch {
    return null;
  }
}

/** Only Wikimedia image hosts over HTTPS; these are also the only ones the CSP allows. */
export function isAllowedImage(url: string): boolean {
  const parsed = parse(url);
  return parsed?.protocol === 'https:' && IMAGE_HOSTS.has(parsed.hostname);
}

export function isWikipediaPage(url: string): boolean {
  const parsed = parse(url);
  return (
    parsed?.protocol === 'https:' && parsed.hostname === 'en.wikipedia.org'
  );
}
