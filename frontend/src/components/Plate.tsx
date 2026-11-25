/** An illustration from Wikipedia, with its caption and source. Disappears if it fails to load. */
import { useState } from 'react';
import type { Illustration } from '../lib/api';
import { isAllowedImage, isWikipediaPage } from '../lib/links';
import styles from './Plate.module.css';

interface PlateProps {
  illustration: Illustration;
  /** Load immediately (for the first image on screen). */
  eager?: boolean;
  className?: string;
}

export function Plate({ illustration, eager = false, className }: PlateProps) {
  const [failed, setFailed] = useState(false);
  if (failed || !isAllowedImage(illustration.image_url)) return null;
  const ratio =
    illustration.width && illustration.height
      ? `${illustration.width} / ${illustration.height}`
      : undefined;
  return (
    <figure
      className={className ? `${styles.plate} ${className}` : styles.plate}
    >
      <div className={styles.frame} style={{ aspectRatio: ratio }}>
        <img
          src={illustration.image_url}
          alt={illustration.caption}
          width={illustration.width ?? undefined}
          height={illustration.height ?? undefined}
          loading={eager ? 'eager' : 'lazy'}
          decoding="async"
          referrerPolicy="no-referrer"
          onError={() => setFailed(true)}
        />
      </div>
      <figcaption className={styles.caption}>
        {illustration.caption}{' '}
        {isWikipediaPage(illustration.page_url) && (
          <a
            href={illustration.page_url}
            target="_blank"
            rel="noreferrer noopener"
            className={styles.source}
          >
            Wikipedia
          </a>
        )}
      </figcaption>
    </figure>
  );
}
