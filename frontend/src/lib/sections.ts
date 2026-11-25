/** Splitting lesson Markdown so illustrations can sit between sections. */

/** Split at level-2 headings, ignoring lines inside fenced code. */
export function splitSections(markdown: string): string[] {
  const sections: string[] = [];
  let current: string[] = [];
  let fence: string | null = null;
  for (const line of markdown.split('\n')) {
    const fenceMatch = /^\s*(```|~~~)/.exec(line);
    if (fenceMatch) {
      if (fence === null) fence = fenceMatch[1];
      else if (fence === fenceMatch[1]) fence = null;
    }
    if (fence === null && /^##\s/.test(line) && current.join('').trim()) {
      sections.push(current.join('\n'));
      current = [];
    }
    current.push(line);
  }
  if (current.join('').trim()) sections.push(current.join('\n'));
  return sections;
}

/** After which section each illustration goes: spread evenly through the text. */
export function placements(sections: number, illustrations: number): number[] {
  return Array.from({ length: illustrations }, (_, index) =>
    Math.max(
      0,
      Math.min(
        sections - 1,
        Math.round(((index + 1) * sections) / (illustrations + 1)) - 1,
      ),
    ),
  );
}
