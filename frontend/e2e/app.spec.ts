import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

const CV = `Ada Lovelace
Backend Engineer

Experience
Backend Engineer, Acme Payments (2022-2024)
Built REST APIs in Python with FastAPI and SQLAlchemy, serving two million requests per day.
Designed PostgreSQL schemas and tuned slow queries with indexes.
Added pytest suites with 90% coverage and ran them in GitHub Actions.

Frontend Developer, Globex (2020-2022)
Shipped React and TypeScript dashboards for logistics customers.`

async function signUp(page: Page) {
  await page.goto('/login')
  await page.getByPlaceholder('ada@example.com').fill(`e2e-${Date.now()}@example.com`)
  await page.getByPlaceholder('••••••••').fill('correct horse battery')
  // Turnstile's test site key passes invisibly; the button waits for its token.
  await page.getByRole('button', { name: 'Create account' }).last().click()
  await expect(page.getByText('Get set up')).toBeVisible()
}

test('sign up, index a CV, analyze a job, edit and save, then track it', async ({ page }) => {
  await signUp(page)

  // CV
  await page.getByRole('link', { name: 'My CV' }).first().click()
  await page.getByRole('button', { name: 'Paste' }).click()
  await page.getByPlaceholder(/Paste the full text of your CV/).fill(CV)
  await page.getByRole('button', { name: 'Index CV' }).click()
  await expect(page.getByText(/chunks/).first()).toBeVisible()

  // Analyze a sample posting: the trace streams, then the review pause appears
  await page.getByRole('link', { name: 'Analyze a job' }).first().click()
  await page.getByRole('button', { name: /Northwind Pay/ }).click()
  await page.getByRole('button', { name: /Analyze fit/ }).click()
  await expect(page.getByText('Agent trace')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Cover letter', exact: true })).toBeVisible()
  await expect(page.getByText('Requirement by requirement')).toBeVisible()
  await expect(page).toHaveURL(/\/analyze\/[0-9a-f-]{36}$/)

  // The review survives a full page reload (state comes from the checkpointer)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Cover letter', exact: true })).toBeVisible()

  // Edit the letter and save our version
  const letter = page.locator('textarea').last()
  await letter.fill('Hello Northwind, this is my own letter.')
  await expect(page.getByText('edited by you')).toBeVisible()
  await page.getByRole('button', { name: /Save my version/ }).click()
  await expect(page.getByText('Saved to your tracker')).toBeVisible()

  // Tracker: card is in Saved; drag it to Applied and confirm it persists
  await page.getByRole('button', { name: /Open tracker/ }).click()
  const card = page.locator('[draggable="true"]').first()
  await expect(card).toContainText('Senior Backend Engineer')
  const applied = page.locator('div.glass', { hasText: 'Applied' }).first()
  await card.dragTo(applied)
  await expect(applied.locator('[draggable="true"]')).toHaveCount(1)
  await page.reload()
  await expect(page.locator('div.glass', { hasText: 'Applied' }).first().locator('[draggable="true"]')).toHaveCount(1)

  // Drawer shows the edited letter
  await page.locator('[draggable="true"]').first().click()
  await expect(page.getByText('Hello Northwind, this is my own letter.')).toBeVisible()
})

test('one-click demo account is seeded and replays a sample run', async ({ page }) => {
  await page.goto('/login')
  await page.getByRole('button', { name: /Explore the demo/ }).click()
  await expect(page.getByText('Demo account.')).toBeVisible()

  await page.getByRole('link', { name: 'Tracker' }).first().click()
  await expect(page.locator('[draggable="true"]')).toHaveCount(2)

  await page.getByRole('link', { name: 'Analyze a job' }).first().click()
  await page.getByRole('button', { name: /Helix Health/ }).click()
  await page.getByRole('button', { name: /Analyze fit/ }).click()
  await expect(page.getByRole('heading', { name: 'Machine Learning Platform Engineer' })).toBeVisible()

  // A recorded revision suggestion replays instantly
  await page.getByRole('button', { name: 'Revise' }).click()
  await page.getByRole('button', { name: 'Make it shorter' }).click()
  await page.getByRole('button', { name: 'Send feedback' }).click()
  await expect(page.getByText('revision 1')).toBeVisible()

  await page.getByRole('button', { name: /Approve & save/ }).click()
  await expect(page.getByText('Saved to your tracker')).toBeVisible()
})

test('session survives a reload and sign-out returns to login', async ({ page }) => {
  await signUp(page)
  await page.reload()
  await expect(page.getByText('Get set up')).toBeVisible()
  await page.getByTitle('Sign out').first().click()
  await expect(page).toHaveURL(/\/login$/)
  await page.reload()
  await expect(page.getByRole('heading', { name: /Start applying smarter/ })).toBeVisible()
})
