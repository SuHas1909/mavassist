import { test, expect } from '@playwright/test';

const API = process.env.API_URL || 'http://127.0.0.1:8000';
const password = 'Browser-pass123!';

async function registerStudent(page: import('@playwright/test').Page) {
  const email = `sprint2-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
  await page.goto('/');
  await page.getByRole('button', { name: 'Create an account', exact: true }).click();
  await page.getByLabel('Full name').fill('Browser Student');
  await page.getByLabel('Email address').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Create student account' }).click();
  await expect(page.getByRole('heading', { name: 'Find your next step.' })).toBeVisible();
  return email;
}

test.describe('MavAssist E2E Test Suite', () => {

  test('TC-01 (FR-02): user can log in and reach the directory dashboard', async ({ page }) => {
    const email = await registerStudent(page);
    await page.getByRole('button', { name: 'Sign out' }).click();
    await page.getByLabel('Email address').fill(email);
    await page.getByLabel('Password', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Find your next step.' })).toBeVisible();
  });

  test('TC-02 (NFR-03): student is blocked from admin features', async ({ page, request }) => {
    await registerStudent(page);
    await expect(page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name: 'Manage resources' })).toHaveCount(0);

    const token = await page.evaluate(() => sessionStorage.getItem('mavassist-token'));
    expect(token).toBeTruthy();
    const response = await request.get(`${API}/api/admin/services`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(response.status()).toBe(403);
  });

  test('TC-03 (FR-01): directory search and resource entries load', async ({ page }) => {
    await registerStudent(page);
    await expect(page.getByLabel('Search campus services')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Find your next step.' })).toBeVisible();
    await expect(page.locator('.office-list').getByRole('listitem').first()).toBeVisible();
  });
});