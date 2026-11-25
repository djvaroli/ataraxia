/**
 * A remark plugin that sets typographic quotes, apostrophes, dashes, and
 * ellipses in lesson text. Code, inline code, and math are left untouched.
 */

interface MdNode {
  type: string;
  value?: unknown;
  children?: MdNode[];
}

const VERBATIM = new Set(['code', 'inlineCode', 'math', 'inlineMath', 'html']);
const BLOCKS = new Set([
  'paragraph',
  'heading',
  'listItem',
  'tableCell',
  'blockquote',
  'footnoteDefinition',
]);

const OPENING = /[\s([{—–-]/;
const WORD = /[\p{L}\p{N}]/u;

/** Typographic punctuation for `text`, given the character that came before it. */
export function smarten(text: string, before: string): string {
  const source = text
    .replace(/---/g, '—')
    .replace(/--/g, '–')
    .replace(/\.\.\./g, '…');
  let out = '';
  let previous = before;
  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    const next = source[index + 1] ?? '';
    let replacement = char;
    const atStart = previous === '' || OPENING.test(previous);
    if (char === "'") {
      if (WORD.test(previous) && WORD.test(next)) replacement = '’';
      else replacement = atStart ? '‘' : '’';
    } else if (char === '"') {
      replacement = atStart ? '“' : '”';
    }
    out += replacement;
    previous = char;
  }
  return out;
}

export function remarkTypography() {
  return (tree: MdNode) => {
    let previous = '';
    const visit = (node: MdNode) => {
      if (VERBATIM.has(node.type)) {
        previous = 'x';
        return;
      }
      if (BLOCKS.has(node.type)) previous = '';
      if (node.type === 'text' && typeof node.value === 'string') {
        const value = node.value;
        node.value = smarten(value, previous);
        previous = value.at(-1) ?? previous;
        return;
      }
      node.children?.forEach(visit);
    };
    visit(tree);
  };
}
