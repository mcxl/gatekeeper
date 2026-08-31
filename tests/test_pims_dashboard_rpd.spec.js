const fs = require('fs');
const path = require('path');

function resolveCliBundledPlaywrightTest() {
  let current = path.dirname(require.main.filename);
  while (current !== path.dirname(current)) {
    const packageJson = path.join(current, 'package.json');
    const testEntry = path.join(current, 'test.js');
    if (fs.existsSync(packageJson) && fs.existsSync(testEntry)) {
      const packageMetadata = JSON.parse(fs.readFileSync(packageJson, 'utf8'));
      if (packageMetadata.name === 'playwright') return testEntry;
    }
    current = path.dirname(current);
  }
  throw new Error('Unable to locate the Playwright test runner.');
}

const { test, expect } = require(resolveCliBundledPlaywrightTest());
test.use({ channel: 'chrome' });

const DASHBOARD_PATH = path.join(
  __dirname,
  '..',
  'frontend',
  'pims_dashboard_rpd.html',
);

function dashboardHtmlWithoutExternalStartup() {
  return fs.readFileSync(DASHBOARD_PATH, 'utf8')
    .replace(
      '<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js"></script>',
      '<script>window.supabase = { createClient: () => ({}) };</script>',
    )
    .replace(
      '<script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>',
      '<script>window.XLSX = {};</script>',
    )
    .replace(/\ninitDashboard\(\);\r?\n/, '\n');
}

test('July Month shows the reviewed 91% compliance snapshot as the main value', async ({ page }) => {
  await page.setContent(dashboardHtmlWithoutExternalStartup());
  await page.evaluate(() => {
    const RealDate = window.Date;
    const fixedNow = new RealDate('2026-07-28T12:00:00+10:00');
    class FixedDate extends RealDate {
      constructor(...args) {
        super(...(args.length ? args : [fixedNow]));
      }

      static now() {
        return fixedNow.valueOf();
      }
    }
    window.Date = FixedDate;
    filtered = [];
    kpiPeriod = 'month';
    renderManagerBoard();
  });

  await expect(page.locator('#metricComplianceValue')).toHaveText('91%');
  await expect(page.locator('#metricComplianceTarget')).toContainText('186/204');
  await expect(page.locator('#metricComplianceDelta')).toContainText('reviewed July snapshot');
});

test('current month explains a zero compliance rate with its assessed counts', async ({ page }) => {
  await page.setContent(dashboardHtmlWithoutExternalStartup());
  await page.evaluate(() => {
    const RealDate = window.Date;
    const fixedNow = new RealDate('2026-08-31T12:00:00+10:00');
    class FixedDate extends RealDate {
      constructor(...args) {
        super(...(args.length ? args : [fixedNow]));
      }

      static now() {
        return fixedNow.valueOf();
      }
    }
    window.Date = FixedDate;
    filtered = Array.from({ length: 9 }, (_, index) => ({
      observation_date: `2026-08-${String(11 + (index % 3)).padStart(2, '0')}`,
      conformance_status: 'NCR',
    }));
    kpiPeriod = 'month';
    renderManagerBoard();
  });

  await expect(page.locator('#metricComplianceValue')).toHaveText('0%');
  await expect(page.locator('#metricComplianceTarget')).toHaveText(
    'Target: 85% · 0 of 9 compliant · 9 NCR',
  );
});
