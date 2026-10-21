/**
 * Travel Booking KPI Tracker - Apps Script (v2, columns found by header name)
 *
 * What this does, in plain words:
 * - Reads the "Weekly KPIs" tab (you import kpi_weekly.csv there once)
 * - Checks the last weeks for anomalies: a week is flagged when bookings,
 *   realized revenue or cancellation rate is |z| >= 3 vs the previous
 *   4-week average (same rule as the Python pipeline)
 * - Emails a short snapshot to stakeholders
 * - setupTrigger() makes it run every Monday at 8am on its own
 *
 * Setup (in YOUR Google account, ~10 minutes):
 * 1. Create a Google Sheet named: Travel Booking KPI Tracker
 * 2. File > Import > Upload kpi_weekly.csv > "Insert new sheet(s)"
 *    Rename that tab to exactly: Weekly KPIs
 * 3. Extensions > Apps Script > delete the default code > paste this
 *    whole file > Save
 * 4. Change RECIPIENTS below to your own email for the first test
 * 5. Select function sendSnapshotNow > Run > approve the permission prompt
 *    You should receive the snapshot email. That email is your proof.
 * 6. Then select setupTrigger > Run once. Done - it runs weekly.
 */
const RECIPIENTS = ['your-email@example.com'];
const Z_THRESHOLD = 3.0;
const BASELINE_WEEKS = 4;
const SHEET_NAME = 'Weekly KPIs';
const CHECK_COLUMNS = ['bookings', 'realized_revenue_eur', 'cancellation_rate'];

function getSheet_() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  if (!sheet) throw new Error('Tab not found: ' + SHEET_NAME + ' - import kpi_weekly.csv and rename the tab first.');
  return sheet;
}

function flagAnomalies() {
  const values = getSheet_().getDataRange().getValues();
  const header = values[0].map(h => String(h).trim());
  const colIdx = {};
  CHECK_COLUMNS.forEach(name => {
    colIdx[name] = header.indexOf(name);
    if (colIdx[name] === -1) throw new Error('Column missing in sheet: ' + name);
  });
  const weekIdx = header.indexOf('arrival_week');
  const rows = values.slice(1);
  const flagged = [];
  for (let i = BASELINE_WEEKS; i < rows.length; i++) {
    CHECK_COLUMNS.forEach(name => {
      const c = colIdx[name];
      const window = rows.slice(i - BASELINE_WEEKS, i).map(r => Number(r[c]));
      const mean = window.reduce((a, b) => a + b, 0) / window.length;
      const sd = Math.sqrt(window.map(v => (v - mean) ** 2).reduce((a, b) => a + b, 0) / (window.length - 1));
      if (sd > 0) {
        const z = (Number(rows[i][c]) - mean) / sd;
        if (Math.abs(z) >= Z_THRESHOLD) {
          flagged.push({ week: rows[i][weekIdx], metric: name, value: rows[i][c], z: z.toFixed(2) });
        }
      }
    });
  }
  return flagged;
}

function sendSnapshotNow() {
  const values = getSheet_().getDataRange().getValues();
  const header = values[0].map(h => String(h).trim());
  const last = values[values.length - 1];
  const get = name => last[header.indexOf(name)];
  const anomalies = flagAnomalies();
  let body = 'Travel Booking KPI snapshot\n'
    + 'Latest week: ' + get('arrival_week') + '\n'
    + 'Bookings: ' + get('bookings') + '\n'
    + 'Realized revenue (EUR): ' + get('realized_revenue_eur') + '\n'
    + 'Cancellation rate: ' + get('cancellation_rate') + '\n';
  body += anomalies.length
    ? '\nAnomalies (|z| >= ' + Z_THRESHOLD + ' vs trailing ' + BASELINE_WEEKS + ' weeks):\n'
      + anomalies.slice(-10).map(a => '- ' + a.week + ' ' + a.metric + ': ' + a.value + ' (z=' + a.z + ')').join('\n')
    : '\nNo anomalies in the checked weeks.';
  MailApp.sendEmail(RECIPIENTS.join(','), 'Travel Booking KPI snapshot', body);
}

function setupTrigger() {
  ScriptApp.newTrigger('sendSnapshotNow').timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(8).create();
}
