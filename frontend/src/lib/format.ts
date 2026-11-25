/** Date, time, and number formatting. Local dates are `YYYY-MM-DD` strings. */

function parseLocalDate(localDate: string): Date {
  const [year, month, day] = localDate.split('-').map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

const weekday = new Intl.DateTimeFormat('en-GB', {
  weekday: 'long',
  timeZone: 'UTC',
});
const dayMonth = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'long',
  timeZone: 'UTC',
});
const monthYear = new Intl.DateTimeFormat('en-GB', {
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
});
const shortDate = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  timeZone: 'UTC',
});

/** "Tuesday, 24 November" */
export function formatDateline(localDate: string): string {
  const date = parseLocalDate(localDate);
  return `${weekday.format(date)}, ${dayMonth.format(date)}`;
}

/** "November 2026" */
export function formatMonth(localDate: string): string {
  return monthYear.format(parseLocalDate(localDate));
}

/** "24 Nov" */
export function formatShortDate(localDate: string): string {
  return shortDate.format(parseLocalDate(localDate));
}

export function localYear(localDate: string): number {
  return Number(localDate.slice(0, 4));
}

/** Monday = 0 … Sunday = 6 */
export function weekdayIndex(localDate: string): number {
  return (parseLocalDate(localDate).getUTCDay() + 6) % 7;
}

/** "14:30" in the owner's time zone. */
export function formatTime(iso: string, timeZone?: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone,
  }).format(new Date(iso));
}

/** "2 December" in the owner's time zone. */
export function formatDay(iso: string, timeZone?: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'long',
    timeZone,
  }).format(new Date(iso));
}

/** "06:00" */
export function formatHour(hour: number): string {
  return `${String(hour).padStart(2, '0')}:00`;
}

export function formatMinutes(minutes: number): string {
  return `${minutes} min`;
}

/** "1 lesson", "3 lessons" */
export function plural(count: number, word: string, many = `${word}s`) {
  return `${count} ${count === 1 ? word : many}`;
}

const ROMAN: [number, string][] = [
  [1000, 'M'],
  [900, 'CM'],
  [500, 'D'],
  [400, 'CD'],
  [100, 'C'],
  [90, 'XC'],
  [50, 'L'],
  [40, 'XL'],
  [10, 'X'],
  [9, 'IX'],
  [5, 'V'],
  [4, 'IV'],
  [1, 'I'],
];

export function roman(value: number): string {
  let rest = value;
  let out = '';
  for (const [amount, numeral] of ROMAN) {
    while (rest >= amount) {
      out += numeral;
      rest -= amount;
    }
  }
  return out;
}
