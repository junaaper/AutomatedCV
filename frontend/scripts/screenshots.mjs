// Walks through the whole app with a fresh account and saves screenshots.
//
//   node scripts/screenshots.mjs [outDir]
//
// Needs the backend on :8000 and the frontend on :5173. Used for visual QA and the README.
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { resolve } from 'node:path'

const BASE = process.env.APP_URL ?? 'http://localhost:5173'
const OUT = resolve(process.argv[2] ?? '../docs/screenshots')
mkdirSync(OUT, { recursive: true })

const CV = `Ada Lovelace
Backend Engineer · London · ada@example.com

Experience

Backend Engineer, Acme Payments (2022–2024)
Built REST APIs in Python with FastAPI and SQLAlchemy, serving two million requests per day.
Designed PostgreSQL schemas, wrote Alembic migrations, and tuned slow queries with indexes, cutting p95 latency of the billing API by 40%.
Added pytest suites with 90% coverage and ran them in GitHub Actions.
Mentored two junior engineers through their first production releases.

Frontend Developer, Globex Logistics (2020–2022)
Shipped React and TypeScript dashboards for logistics customers.
Built a component library with Storybook and raised Lighthouse accessibility scores to 98.
Migrated state management from Redux to TanStack Query.

Education
BSc Computer Science, University of Leeds (2016–2020), first class honours.

Skills
Python, FastAPI, PostgreSQL, SQLAlchemy, pytest, Docker, React, TypeScript, GitHub Actions`

const shot = (page, name, opts = {}) =>
  page.screenshot({ path: `${OUT}/${name}.png`, ...opts }).then(() => console.log('saved', name))

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
page.on('pageerror', (e) => console.error('PAGE ERROR:', e.message))
page.on('console', (m) => m.type() === 'error' && console.error('CONSOLE:', m.text()))

// 1. Landing / auth
await page.goto(`${BASE}/login`)
await page.getByRole('heading', { name: /Start applying smarter/ }).waitFor()
await page.waitForTimeout(2200) // let hero animations settle
await shot(page, '01-login')

// 2. Sign up → overview (onboarding)
await page.getByPlaceholder('ada@example.com').fill(`tour-${Date.now()}@example.com`)
await page.getByPlaceholder('••••••••').fill('correct horse battery')
await page.waitForTimeout(1500) // Turnstile test key auto-passes
await page.getByRole('button', { name: 'Create account' }).last().click()
await page.getByText('Get set up').waitFor()
await page.waitForTimeout(1500)
await shot(page, '02-overview-onboarding')

// 3. CV: paste + probe
await page.getByRole('link', { name: 'My CV' }).first().click()
await page.getByRole('button', { name: 'Paste' }).click()
await page.getByPlaceholder(/Paste the full text of your CV/).fill(CV)
await page.getByRole('button', { name: 'Index CV' }).click()
await page.getByText('Probe your CV').waitFor({ timeout: 60_000 })
await page.getByRole('button', { name: 'Python backend' }).click()
await page.waitForTimeout(2500)
await shot(page, '03-cv')

// 4. Analyze: compose → running → review
await page.getByRole('link', { name: 'Analyze a job' }).first().click()
await page.getByRole('button', { name: /Use a sample posting/ }).click()
await page.waitForTimeout(400)
await shot(page, '04-compose')
await page.getByRole('button', { name: /Analyze fit/ }).click()
await page.getByText('Agent trace').waitFor()
await page.waitForTimeout(1800)
await shot(page, '05-running')
await page.getByRole('heading', { name: 'Cover letter', exact: true }).waitFor({ timeout: 120_000 })
await page.waitForTimeout(2500)
await shot(page, '06-review')
await shot(page, '06-review-full', { fullPage: true })

// 5. Approve → celebration
await page.getByRole('button', { name: /Approve & save/ }).click()
await page.getByText('Saved to your tracker').waitFor({ timeout: 60_000 })
await page.waitForTimeout(1500)
await shot(page, '07-saved')

// 6. Tracker + drawer
await page.getByRole('button', { name: /Open tracker/ }).click()
await page.getByText('Every application').waitFor()
await page.waitForTimeout(1200)
await shot(page, '08-tracker')
await page.locator('[draggable="true"]').first().click()
await page.getByText('Original posting').waitFor()
await page.waitForTimeout(1500)
await shot(page, '09-drawer')
await page.keyboard.press('Escape')

// 7. Overview with data
await page.getByRole('link', { name: 'Overview' }).first().click()
await page.getByText('Recent agent runs').waitFor()
await page.waitForTimeout(1800)
await shot(page, '10-overview')

// 8. Mobile
await page.setViewportSize({ width: 390, height: 844 })
await page.waitForTimeout(800)
await shot(page, '11-mobile-overview')

await browser.close()
