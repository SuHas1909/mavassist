// Capture evidence screenshots of every main screen and assistant state (Chromium, desktop and 360 px).
// Usage (from frontend/):  node ../scripts/capture_screens.mjs <out-dir> [normal|fallback]
//   normal   - API in offline mode: answer, crisis, harm report, violence, not found, greeting, admin, mobile
//   fallback - API with a hosted model configured but unreachable: the cited-source fallback answer
// Needs BASE_URL (default http://127.0.0.1:5173) and, for admin pages, E2E_ADMIN_EMAIL / E2E_ADMIN_PASSWORD.
import {createRequire} from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
const require = createRequire(path.join(process.cwd(), 'package.json'));
const {chromium} = require('@playwright/test');

const out = path.resolve(process.argv[2] || 'screens');
const phase = process.argv[3] || 'normal';
const BASE = process.env.BASE_URL || 'http://127.0.0.1:5173';
fs.mkdirSync(out, {recursive: true});
const shots = [];

async function settle(page) {
  await page.evaluate(async () => {
    const active = document.getAnimations().filter(a => a.playState !== 'finished' && a.effect?.getComputedTiming().iterations !== Infinity);
    await Promise.all(active.map(a => a.finished.catch(() => undefined)));
  });
}
async function shot(page, name) {
  await settle(page);
  // A full-page capture draws sticky elements (navigation bar, question box) at the current scroll position, on top
  // of the content. For the capture only, lay them out in normal flow; the app itself is unchanged.
  await page.evaluate(() => {
    window.__unstuck = [...document.querySelectorAll('*')].filter(el => getComputedStyle(el).position === 'sticky');
    for (const el of window.__unstuck) el.style.setProperty('position', 'static', 'important');
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(200);
  const file = path.join(out, name + '.png');
  await page.screenshot({path: file, fullPage: true, scale: 'css'});
  await page.evaluate(() => { for (const el of window.__unstuck || []) el.style.removeProperty('position'); });
  shots.push(name);
}
async function register(page, label) {
  await page.goto(BASE + '/');
  await page.getByRole('button', {name: 'Create an account', exact: true}).click();
  await page.getByLabel('Full name').fill(label + ' Student');
  await page.getByLabel('Email address').fill(`${label.toLowerCase()}-${Date.now()}@example.com`);
  await page.getByLabel('Password', {exact: true}).fill('Screens-pass123!');
  await page.getByRole('button', {name: 'Create student account'}).click();
  await page.getByRole('heading', {name: 'Find your next step.'}).waitFor();
}
async function ask(page, question, expectText) {
  const answers = page.locator('.conversation>article');
  const before = await answers.count();
  await page.getByLabel('Your campus question').fill(question);
  await page.getByRole('button', {name: 'Send question'}).click();
  await page.waitForFunction(n => document.querySelectorAll('.conversation>article').length > n, before, {timeout: 30000});
  const last = answers.last();
  if (expectText) await last.getByText(expectText, {exact: false}).first().waitFor({timeout: 30000});
  await page.waitForTimeout(400);
  return last;
}
async function newAssistant(browser, label, viewport = {width: 1280, height: 900}) {
  const page = await browser.newPage({viewport, reducedMotion: 'reduce'});
  await register(page, label);
  await page.getByRole('navigation', {name: 'Main navigation'}).getByRole('button', {name: 'Ask MavAssist'}).click();
  return page;
}

const browser = await chromium.launch();
try {
  if (phase === 'fallback') {
    const page = await newAssistant(browser, 'Fallback');
    await ask(page, 'I have paid extra tuition fee to accounts how to get refund!', 'Student Accounts');
    await shot(page, 'assistant-fallback-desktop');
  } else {
    // Student screens
    let page = await browser.newPage({viewport: {width: 1280, height: 900}, reducedMotion: 'reduce'});
    await page.goto(BASE + '/'); await page.getByRole('heading', {name: 'Welcome back.'}).waitFor();
    await shot(page, 'sign-in-desktop');
    await page.getByRole('button', {name: 'Create an account', exact: true}).click(); await shot(page, 'register-desktop');
    await register(page, 'Screens'); await shot(page, 'directory-desktop');
    await page.getByLabel('Search campus services').fill('tuition'); await page.getByRole('button', {name: 'Search', exact: true}).click();
    await page.getByRole('button', {name: 'Student Accounts', exact: true}).waitFor(); await shot(page, 'search-results-desktop');
    await page.getByRole('button', {name: 'Student Accounts', exact: true}).click(); await page.getByRole('dialog').waitFor();
    await shot(page, 'service-detail-desktop');
    await page.getByRole('button', {name: 'Save resource', exact: true}).click(); await page.getByRole('button', {name: 'Close resource'}).click();
    await page.getByRole('button', {name: 'Saved resources', exact: true}).click(); await shot(page, 'saved-resources-desktop');
    await page.getByRole('button', {name: 'Recently viewed', exact: true}).click(); await shot(page, 'recently-viewed-desktop');
    await page.getByRole('navigation', {name: 'Main navigation'}).getByRole('button', {name: 'Ask MavAssist'}).click();
    await shot(page, 'assistant-empty-desktop');
    // Assistant states (each in a fresh conversation so the screenshot shows one state)
    const states = [
      ['assistant-answer-desktop', 'I have paid extra tuition fee to accounts how to get refund!', 'Sources'],
      ['assistant-crisis-desktop', 'I want to end my life', '988'],
      ['assistant-harm-report-desktop', 'someone mollested me', 'not your fault'],
      ['assistant-violence-desktop', 'i wanna hit someone', 'not a place for violence'],
      ['assistant-not-found-desktop', 'tell me a joke', 'Not found in MavAssist'],
      ['assistant-greeting-desktop', 'hi', null],
    ];
    for (const [name, question, expectText] of states) {
      const p = await newAssistant(browser, name.split('-')[1]);
      await ask(p, question, expectText);
      await shot(p, name); await p.close();
    }
    // Mobile 360 px
    page = await newAssistant(browser, 'Mobile', {width: 360, height: 800});
    await page.getByRole('navigation', {name: 'Main navigation'}).getByRole('button', {name: 'Explore resources', exact: true}).click().catch(() => {});
    await shot(page, 'directory-360px');
    await page.getByRole('navigation', {name: 'Main navigation'}).getByRole('button', {name: 'Ask MavAssist'}).click();
    await ask(page, 'I need help with tuition payment.', 'Sources'); await shot(page, 'assistant-360px');
    await page.close();
    // Administrator screens
    if (process.env.E2E_ADMIN_EMAIL && process.env.E2E_ADMIN_PASSWORD) {
      page = await browser.newPage({viewport: {width: 1280, height: 900}, reducedMotion: 'reduce'});
      await page.goto(BASE + '/');
      await page.getByLabel('Email address').fill(process.env.E2E_ADMIN_EMAIL);
      await page.getByLabel('Password', {exact: true}).fill(process.env.E2E_ADMIN_PASSWORD);
      await page.getByRole('button', {name: 'Sign in', exact: true}).click();
      await page.getByRole('button', {name: 'Manage resources', exact: true}).click(); await shot(page, 'admin-resources-desktop');
      await page.getByRole('button', {name: 'Add service'}).click(); await shot(page, 'admin-service-editor-desktop');
      await page.keyboard.press('Escape').catch(() => {});
      await page.getByRole('button', {name: 'Categories', exact: true}).click(); await shot(page, 'admin-categories-desktop');
      await page.getByRole('button', {name: 'Notices', exact: true}).click(); await shot(page, 'admin-notices-desktop');
      await page.getByRole('button', {name: 'Usage insights', exact: true}).click();
      await page.getByRole('heading', {name: 'Usage insights'}).waitFor(); await shot(page, 'admin-insights-desktop');
    } else {
      throw new Error('Set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD to capture the administrator screens');
    }
  }
} finally {
  await browser.close();
}
fs.writeFileSync(path.join(out, `screens-${phase}.json`), JSON.stringify({phase, base: BASE, shots}, null, 2));
console.log(`captured ${shots.length} screens (${phase}) into ${out}`);
