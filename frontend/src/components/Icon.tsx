/** A few hand-drawn stroke icons. Decorative unless a label is given. */
import type { SVGProps } from 'react';

export type IconName =
  'back' | 'bookmark' | 'bookmarked' | 'menu' | 'check' | 'arrow' | 'close';

const PATHS: Record<IconName, string> = {
  back: 'M14.5 5.5 8 12l6.5 6.5',
  bookmark: 'M7 4.5h10v15l-5-3.6-5 3.6z',
  bookmarked: 'M7 4.5h10v15l-5-3.6-5 3.6z',
  menu: 'M5.5 12h.01M12 12h.01M18.5 12h.01',
  check: 'm5.5 12.5 4 4 9-9.5',
  arrow: 'M4.5 12h14.5m-5-5 5 5-5 5',
  close: 'm6.5 6.5 11 11m0-11-11 11',
};

interface IconProps extends SVGProps<SVGSVGElement> {
  name: IconName;
  size?: number;
}

export function Icon({ name, size = 22, ...props }: IconProps) {
  const filled = name === 'bookmarked';
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor"
      strokeWidth={name === 'menu' ? 2.6 : 1.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
