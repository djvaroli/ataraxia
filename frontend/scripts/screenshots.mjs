// Screenshots of the demo build for design review. Run through scripts/screenshots.sh.
// Usage: node screenshots.mjs <base-url> <out-dir> [name-filter]
import { chromium } from 'playwright';

const [base, out, filter = ''] = process.argv.slice(2);
const phone = { width: 390, height: 844 };
const desktop = { width: 1280, height: 800 };

const shots = [
  { name: 'today', path: '/?scenario=ready', full: true },
  { name: 'today-preparing', path: '/?scenario=preparing&advance=off' },
  { name: 'today-failed', path: '/?scenario=failed' },
  { name: 'today-waiting', path: '/?scenario=waiting' },
  { name: 'today-limit', path: '/?scenario=limit', full: true },
  { name: 'reader', path: '/lessons/l-vermeer' },
  { name: 'reader-full', path: '/lessons/l-vermeer', full: true },
  { name: 'reader-math', path: '/lessons/l-harmonic', scrollTo: 'table' },
  { name: 'reader-code', path: '/lessons/l-hash', scrollTo: 'pre' },
  {
    name: 'reader-end',
    path: '/lessons/l-hash-2',
    scrollTo: '#remember-title',
  },
  {
    name: 'go-deeper',
    path: '/lessons/l-vermeer',
    click: 'button:has-text("Vermeer’s blues")',
  },
  {
    name: 'flag',
    path: '/lessons/l-vermeer',
    click: ['button[aria-label="More"]'],
  },
  { name: 'library', path: '/library', full: true },
  { name: 'progress', path: '/progress', full: true },
  { name: 'settings', path: '/settings', full: true },
  { name: 'sign-in', path: '/?auth=firebase' },
  { name: 'desktop-today', path: '/?scenario=ready', viewport: desktop },
  { name: 'desktop-reader', path: '/lessons/l-harmonic', viewport: desktop },
];

const browser = await chromium.launch();
for (const scheme of ['light', 'dark']) {
  for (const shot of shots) {
    if (filter && !shot.name.includes(filter)) continue;
    const context = await browser.newContext({
      viewport: shot.viewport ?? phone,
      deviceScaleFactor: shot.viewport ? 1 : 2,
      colorScheme: scheme,
      timezoneId: 'Europe/London',
    });
    const page = await context.newPage();
    await page.goto(base + shot.path, { waitUntil: 'networkidle' });
    await page.waitForTimeout(700);
    if (shot.scrollTo) {
      await page.locator(shot.scrollTo).first().scrollIntoViewIfNeeded();
      await page.evaluate(() => window.scrollBy(0, -120));
      await page.waitForTimeout(400);
    }
    for (const selector of [shot.click ?? []].flat()) {
      await page.locator(selector).first().click();
      await page.waitForTimeout(500);
    }
    await page.screenshot({
      path: `${out}/${shot.name}-${scheme}.png`,
      fullPage: shot.full ?? false,
    });
    await context.close();
  }
}
await browser.close();
