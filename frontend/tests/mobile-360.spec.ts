import {expect,test} from '@playwright/test';

test('360 px student flow stays within the viewport',async({page})=>{
  await page.setViewportSize({width:360,height:800});
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Welcome back.'})).toBeVisible();
  await page.screenshot({path:'../test-evidence-2026-11-09/screenshots/sign-in-360px.png',fullPage:true});

  await page.getByRole('button',{name:'Create an account',exact:true}).click();
  await page.getByLabel('Full name').fill('Mobile Test Student');
  await page.getByLabel('Email address').fill(`mobile-${Date.now()}@example.com`);
  await page.getByLabel('Password',{exact:true}).fill('Mobile-pass123!');
  await page.getByRole('button',{name:'Create student account'}).click();
  await expect(page.getByRole('heading',{name:'Find your next step.'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.screenshot({path:'../test-evidence-2026-11-09/screenshots/directory-360px.png',fullPage:true});

  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'Ask MavAssist'}).click();
  await page.getByLabel('Your campus question').fill('I need help with tuition payment.');
  await page.getByRole('button',{name:'Send question'}).click();
  await expect(page.locator('.answer-paragraph').first()).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.screenshot({path:'../test-evidence-2026-11-09/screenshots/assistant-360px.png',fullPage:true});
});
