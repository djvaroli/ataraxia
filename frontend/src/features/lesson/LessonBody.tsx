/**
 * Renders model-written Markdown as inert text: no raw HTML, no images, and no
 * links (link syntax renders as its plain text). Math goes through KaTeX with
 * `trust: false`, so commands such as \href cannot create links either.
 */
import 'katex/dist/katex.min.css';
import { Fragment, memo, type ReactNode } from 'react';
import Markdown, { type Components } from 'react-markdown';
import rehypeKatex from 'rehype-katex';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import { Plate } from '../../components/Plate';
import type { Illustration } from '../../lib/api';
import { placements, splitSections } from '../../lib/sections';
import { remarkTypography } from '../../lib/typography';
import styles from './lesson.module.css';

const components: Components = {
  a: ({ children }) => <span>{children}</span>,
  h1: ({ children }) => <h2>{children}</h2>,
  h4: ({ children }) => <h4>{children}</h4>,
  h5: ({ children }) => <h4>{children}</h4>,
  h6: ({ children }) => <h4>{children}</h4>,
  table: ({ children }) => (
    <div
      className={styles.tableWrap}
      role="region"
      aria-label="Table"
      tabIndex={0}
    >
      <table>{children}</table>
    </div>
  ),
  pre: ({ children }) => <pre tabIndex={0}>{children}</pre>,
};

const katexOptions = { throwOnError: false, strict: 'ignore', trust: false };

function Section({ markdown }: { markdown: string }) {
  return (
    <Markdown
      skipHtml
      disallowedElements={['img']}
      unwrapDisallowed
      remarkPlugins={[remarkGfm, remarkMath, remarkTypography]}
      rehypePlugins={[[rehypeKatex, katexOptions]]}
      components={components}
    >
      {markdown}
    </Markdown>
  );
}

interface LessonBodyProps {
  markdown: string;
  /** Illustrations to place between sections (the first one is shown above the text). */
  illustrations: Illustration[];
}

/** Memoized: parsing Markdown and typesetting math is the reader's costliest work. */
export const LessonBody = memo(function LessonBody({
  markdown,
  illustrations,
}: LessonBodyProps) {
  const sections = splitSections(markdown);
  const after = placements(sections.length, illustrations.length);
  return (
    <div className={styles.body}>
      {sections.map((section, index) => {
        const plates: ReactNode[] = illustrations
          .filter((_, i) => after[i] === index)
          .map((illustration) => (
            <Plate key={illustration.image_url} illustration={illustration} />
          ));
        return (
          <Fragment key={index}>
            <div className={styles.section}>
              <Section markdown={section} />
            </div>
            {plates}
          </Fragment>
        );
      })}
    </div>
  );
});
