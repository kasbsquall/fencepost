// Record real UI motion with Playwright -> webm (then convert to mp4 with ffmpeg),
// for embedding as a moving product shot via VideoShot3D. Recorded video reads far
// more "alive" than a static screenshot.
//
// Usage:
//   node record.js <url> <out.webm> [--scroll N] [--click "Button name"] [--wait MS] [--w 1600] [--h 1000] [--dark]
//
// Then: ffmpeg -y -i out.webm -c:v libx264 -pix_fmt yuv420p -crf 20 -an out.mp4
// and copy out.mp4 into remotion/public/vid/. Reference it with
//   <VideoShot3D src="vid/out.mp4" .../>
//
// Needs playwright (or @playwright/test) installed. Run from a project that has it,
// e.g. `node /path/to/record.js ...` where require can resolve playwright.
let chromium;
try { chromium = require('playwright').chromium; }
catch (e) { chromium = require('@playwright/test').chromium; }
const fs = require('fs');
const path = require('path');

function arg(flag, def) {
  const i = process.argv.indexOf(flag);
  return i > -1 ? process.argv[i + 1] : def;
}
const has = (flag) => process.argv.includes(flag);

const url = process.argv[2];
const out = process.argv[3];
if (!url || !out) { console.error('usage: node record.js <url> <out.webm> [--scroll N] [--click "Name"] [--wait MS] [--dark]'); process.exit(1); }
const W = parseInt(arg('--w', '1600'), 10);
const H = parseInt(arg('--h', '1000'), 10);
const scroll = parseInt(arg('--scroll', '0'), 10);
const click = arg('--click', '');
const wait = parseInt(arg('--wait', '2600'), 10);

async function slowScroll(page, total, step = 6, delay = 14) {
  for (let y = 0; y < total; y += step) { await page.mouse.wheel(0, step); await page.waitForTimeout(delay); }
}

(async () => {
  const dir = path.dirname(path.resolve(out));
  fs.mkdirSync(dir, {recursive: true});
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: {width: W, height: H},
    colorScheme: has('--dark') ? 'dark' : 'light',
    recordVideo: {dir, size: {width: W, height: H}},
  });
  const page = await ctx.newPage();
  await page.goto(url, {waitUntil: 'networkidle', timeout: 60000});
  await page.waitForTimeout(wait);
  if (scroll > 0) await slowScroll(page, scroll);
  if (click) {
    const btn = page.getByRole('button', {name: new RegExp(click, 'i')});
    await btn.scrollIntoViewIfNeeded().catch(() => {});
    await page.waitForTimeout(500);
    await btn.click().catch(() => {});
    await page.waitForTimeout(4500);
  }
  const vid = page.video();
  await ctx.close();
  const src = await vid.path();
  fs.renameSync(src, path.resolve(out));
  await browser.close();
  console.log('saved', out, '(convert to mp4 with ffmpeg, then place in public/vid/)');
})();
