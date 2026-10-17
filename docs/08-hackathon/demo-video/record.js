const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");
const segments = require("./segments");

// QA finding (2026-10-17): confirmed there is NO UI path anywhere (approve response,
// compliance review results page, approval row link) that surfaces the resulting
// Decision's id after approving a REVIEW-outcome request -- only `/evidence`'s lookup
// form exists, and it requires already knowing the id. Querying it directly here is the
// same kind of legitimate pre-staging demo-scenario.md already does for the blockchain
// anchor ("pre-submit a few minutes before the live demo") -- a presenter would need to
// know this id from some out-of-band source too, since the product doesn't surface it.
function findDecisionIdForContract(contractId) {
  const sql = `SELECT d.id FROM decisions d JOIN contract_versions cv ON d.contract_version_id = cv.id WHERE cv.contract_id = '${contractId}' ORDER BY d.created_at DESC LIMIT 1;`;
  const out = execSync(
    `docker compose exec -T postgres psql -U jurisense -d jurisense -t -A -c "${sql}"`,
    { cwd: "/home/santos/Astreus_dev/JuriSense", encoding: "utf8" }
  ).trim();
  return out || null;
}

const BASE = "http://localhost:3000";
const ADMIN = { email: "admin@acme-tecnologia.demo", password: "DemoJuriSense2026!" };
const LEGAL = { email: "legal@acme-tecnologia.demo", password: "DemoJuriSense2026!" };
const V1_PDF = "/home/santos/Astreus_dev/JuriSense/docs/08-hackathon/demo-assets/contracts/clouddocs-saas-v1-original.pdf";
const V2_PDF = "/home/santos/Astreus_dev/JuriSense/docs/08-hackathon/demo-assets/contracts/clouddocs-saas-v2-corrigido.pdf";
// Digits only, real CNPJ checksum (app/suppliers/domain/tax_id.py). A fresh branch
// number per recording run avoids depending on deleting the previous run's supplier --
// evidence/decisions are append-only by DB trigger (confirmed: DELETE is rejected), so
// a prior run's CloudDocs supplier+contract+decision chain can never be cleaned up, only
// left in place as harmless orphaned test data.
const CNPJ = "98765432798122";

const durations = JSON.parse(
  fs.readFileSync(path.join(__dirname, "durations.json"), "utf8")
);
const BUFFER_MS = 700; // small breathing room after each narration line

function segDwell(id) {
  return Math.round((durations[id] || 4) * 1000) + BUFFER_MS;
}

async function login(page, { email, password }) {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.getByLabel("Work email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 15000 });
}

async function pollUntil(page, checkFn, { timeoutMs = 90000, intervalMs = 3000, label = "" } = {}) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await checkFn()) return true;
    await page.waitForTimeout(intervalMs);
    await page.reload({ waitUntil: "networkidle" });
  }
  console.warn(`WARNING: pollUntil timed out waiting for: ${label}`);
  return false;
}

async function main() {
  const browser = await chromium.launch({ headless: true });

  const adminCtx = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: { dir: path.join(__dirname, "video"), size: { width: 1280, height: 720 } },
  });
  const page = await adminCtx.newPage();
  _lastPage = page;

  const adminStart = Date.now();
  const timeline = { admin: [], legal: [] };
  let legalStart = 0;
  let legalStartSet = false;
  // Records the offset, in THIS segment's own video file, at which the UI visually
  // reaches the state this segment's narration describes -- i.e. right before the
  // dwell that stands in for "the narration is playing now". Called right before each
  // `waitForTimeout(segDwell(...))`, not at the top of the segment block, since the
  // real network/UI action time before that point is unpredictable (Gemini extraction
  // latency, polling reloads) and must NOT be counted as part of the narration window.
  const mark = (id) => {
    console.log(`=== [${id}] dwell ${(segDwell(id) / 1000).toFixed(1)}s ===`);
    const bucket = legalStartSet ? timeline.legal : timeline.admin;
    const base = legalStartSet ? legalStart : adminStart;
    bucket.push({ id, offsetSec: (Date.now() - base) / 1000 });
  };
  const log = (id) => console.log(`\n--- starting [${id}] ---`);

  // intro
  log("intro");
  await login(page, ADMIN);
  mark("intro");
  await page.waitForTimeout(segDwell("intro"));

  // create-supplier
  log("supplier-create");
  await page.goto(`${BASE}/suppliers/new`, { waitUntil: "networkidle" });
  await page.getByLabel("Legal name").fill("CloudDocs Software Ltda.");
  await page.getByLabel("Tax ID").fill(CNPJ);
  await page.getByRole("button", { name: "Register supplier" }).click();
  await page.waitForURL(/\/suppliers\/[0-9a-f-]+$/, { timeout: 15000 });
  const supplierUrl = page.url();
  mark("supplier-create");
  await page.waitForTimeout(segDwell("supplier-create"));

  // supplier-check
  log("supplier-check");
  await pollUntil(
    page,
    async () => /completed/i.test(await page.content()),
    { label: "supplier check completed", timeoutMs: 60000 }
  );
  mark("supplier-check");
  await page.waitForTimeout(segDwell("supplier-check"));

  // contract-upload-v1
  log("contract-upload-v1");
  await page.goto(`${BASE}/contracts/new`, { waitUntil: "networkidle" });
  const supplierSelect = page.getByLabel("Supplier");
  // .last(): a prior recording run's "CloudDocs Software Ltda." supplier can't be
  // deleted (its contract/decision/evidence chain is append-only), so more than one
  // may exist by name -- the one just created this run is the most recently added.
  const supplierOptionValue = await supplierSelect
    .locator("option")
    .filter({ hasText: "CloudDocs" })
    .last()
    .getAttribute("value");
  await supplierSelect.selectOption(supplierOptionValue);
  await page.getByLabel("Title").fill("SaaS Agreement — CloudDocs Software");
  const contractTypeField = page.getByLabel("Contract type");
  if (await contractTypeField.count()) {
    const tag = await contractTypeField.evaluate((el) => el.tagName);
    if (tag === "SELECT") await contractTypeField.selectOption({ index: 1 }).catch(() => {});
    else await contractTypeField.fill("MSA").catch(() => {});
  }
  await page.locator('input[type="file"]').setInputFiles(V1_PDF);
  await page.getByRole("button", { name: "Upload contract" }).click();
  await page.waitForURL(/\/contracts\/[0-9a-f-]+$/, { timeout: 20000 });
  const contractUrl = page.url();
  const contractId = contractUrl.split("/").pop();
  mark("contract-upload-v1");
  await page.waitForTimeout(segDwell("contract-upload-v1"));

  // extraction-wait
  log("extraction-wait");
  mark("extraction-wait");
  await page.waitForTimeout(segDwell("extraction-wait"));
  await pollUntil(
    page,
    async () => !/Extraction in progress/i.test(await page.content()),
    { label: "AI extraction (v1)", timeoutMs: 180000 }
  );

  // Handle a needs_confirmation gate if it appears
  const confirmBtn = page.getByRole("button", { name: "Confirm and continue" });
  if (await confirmBtn.count()) {
    const acceptRadios = page.getByLabel(/Accept the AI value as-is/i);
    const n = await acceptRadios.count();
    for (let i = 0; i < n; i++) await acceptRadios.nth(i).check().catch(() => {});
    await confirmBtn.click().catch(() => {});
    await page.waitForTimeout(2000);
  }

  // extraction-result
  log("extraction-result");
  mark("extraction-result");
  await page.waitForTimeout(segDwell("extraction-result"));

  // compliance-review-v1
  log("compliance-review-v1");
  await page.getByRole("button", { name: "Run compliance review" }).click();
  await page.waitForURL(/\/compliance\/reviews\/[0-9a-f-]+/, { timeout: 30000 });
  mark("compliance-review-v1");
  await page.waitForTimeout(segDwell("compliance-review-v1"));

  // compliance-result-v1
  log("compliance-result-v1");
  mark("compliance-result-v1");
  await page.waitForTimeout(segDwell("compliance-result-v1"));

  // contract-upload-v2
  log("contract-upload-v2");
  await page.goto(`${BASE}/contracts/new?contractId=${contractId}`, { waitUntil: "networkidle" });
  await page.locator('input[type="file"]').setInputFiles(V2_PDF);
  await page.getByRole("button", { name: "Upload contract" }).click();
  await page.waitForURL(new RegExp(`/contracts/${contractId}`), { timeout: 20000 });
  mark("contract-upload-v2");
  await page.waitForTimeout(segDwell("contract-upload-v2"));

  // extraction-wait-v2
  log("extraction-wait-v2");
  mark("extraction-wait-v2");
  await page.waitForTimeout(segDwell("extraction-wait-v2"));
  await pollUntil(
    page,
    async () => !/Extraction in progress/i.test(await page.content()),
    { label: "AI extraction (v2)", timeoutMs: 180000 }
  );
  if (await confirmBtn.count()) {
    const acceptRadios = page.getByLabel(/Accept the AI value as-is/i);
    const n = await acceptRadios.count();
    for (let i = 0; i < n; i++) await acceptRadios.nth(i).check().catch(() => {});
    await confirmBtn.click().catch(() => {});
    await page.waitForTimeout(2000);
  }

  // compliance-review-v2
  log("compliance-review-v2");
  await page.getByRole("button", { name: "Run compliance review" }).click();
  await page.waitForURL(/\/compliance\/reviews\/[0-9a-f-]+/, { timeout: 30000 });
  const reviewV2Url = page.url();
  mark("compliance-review-v2");
  await page.waitForTimeout(segDwell("compliance-review-v2"));

  // compliance-result-v2
  log("compliance-result-v2");
  mark("compliance-result-v2");
  await page.waitForTimeout(segDwell("compliance-result-v2"));

  await adminCtx.close(); // flushes admin video segment

  // approval (fresh context as the legal approver)
  const legalCtx = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: { dir: path.join(__dirname, "video"), size: { width: 1280, height: 720 } },
  });
  const legalPage = await legalCtx.newPage();
  legalStart = Date.now();
  legalStartSet = true;
  _lastPage = legalPage;
  await login(legalPage, LEGAL);
  await legalPage.goto(`${BASE}/approvals`, { waitUntil: "networkidle" });
  log("approval");
  // "networkidle" doesn't guarantee client-side hydration finished (hydration is pure
  // JS, no network activity) -- empirically confirmed: without this wait, the Approve
  // click landed on a not-yet-hydrated button (visible, DOM-enabled, Playwright
  // considered it actionable) and silently did nothing, no POST ever fired.
  await legalPage.waitForTimeout(1500);
  // Target the row for THIS run's review specifically -- multiple pending approval
  // requests can coexist (an earlier recording attempt's never got resolved), so
  // `.first()`/`.last()` is a guess; matching the "View compliance review" link's href
  // against the known reviewId is not.
  const reviewId = reviewV2Url.match(/\/compliance\/reviews\/([0-9a-f-]+)/)[1];
  // Each pending request is one <li> (ApprovalRequestRow.tsx) -- no nested <li>s, so
  // this is unambiguous, unlike filtering "li, div".
  const row = legalPage.locator("li").filter({ has: legalPage.locator(`a[href*="${reviewId}"]`) });
  const justification = row.getByLabel("Justification");
  if (await justification.count()) {
    await justification.first().fill("Liability now capped and DPA in place; value still requires Legal sign-off per FIN-003.");
  }
  const approveResponse = legalPage.waitForResponse(
    (resp) => resp.url().includes("/api/approvals/requests/") && resp.url().includes("/approve"),
    { timeout: 15000 },
  );
  await row.getByRole("button", { name: "Approve" }).first().click();
  const resp = await approveResponse;
  console.log("  approve response status:", resp.status());
  await legalPage.waitForTimeout(3000);
  mark("approval");
  await legalPage.waitForTimeout(segDwell("approval"));

  // passport
  log("passport");
  // No UI path surfaces the new Decision's id after approval (confirmed: not in the
  // approve response, not on this results page, not on the approval row) -- looked up
  // directly, same legitimacy as demo-scenario.md's own pre-staged-anchor note.
  const decisionRef = findDecisionIdForContract(contractId);
  console.log("  decisionRef:", decisionRef);
  if (decisionRef) {
    await legalPage.goto(`${BASE}/decisions/${decisionRef}`, { waitUntil: "networkidle" });
  } else {
    await legalPage.goto(reviewV2Url, { waitUntil: "networkidle" });
  }
  mark("passport");
  await legalPage.waitForTimeout(segDwell("passport"));

  // anchor-note (no navigation, just narration over the passport screen)
  log("anchor-note");
  mark("anchor-note");
  await legalPage.waitForTimeout(segDwell("anchor-note"));

  // open-verify
  log("verify-open");
  await legalPage.goto(`${BASE}/verify`, { waitUntil: "networkidle" });
  mark("verify-open");
  await legalPage.waitForTimeout(segDwell("verify-open"));

  // verify-click
  log("verify-click");
  if (decisionRef) {
    await legalPage.getByLabel(/Decision id or evidence hash/i).fill(decisionRef);
  }
  await legalPage.getByRole("button", { name: "Verify" }).click();
  await legalPage.waitForTimeout(3000);
  mark("verify-click");
  await legalPage.waitForTimeout(segDwell("verify-click"));

  // close
  log("close");
  mark("close");
  await legalPage.waitForTimeout(segDwell("close"));

  await legalCtx.close();
  await browser.close();

  fs.writeFileSync(
    path.join(__dirname, "run-info.json"),
    JSON.stringify({ supplierUrl, contractId, reviewV2Url, decisionRef }, null, 2)
  );
  fs.writeFileSync(
    path.join(__dirname, "timeline.json"),
    JSON.stringify(timeline, null, 2)
  );
  console.log("\nDone. run-info.json and timeline.json written.");
}

let _lastPage = null;

main().catch(async (err) => {
  console.error("FATAL:", err);
  try {
    if (_lastPage) {
      await _lastPage.screenshot({ path: path.join(__dirname, "error.png"), fullPage: true });
      console.error("Screenshot saved to error.png");
      console.error("Page URL at failure:", _lastPage.url());
    }
  } catch (e) {
    console.error("Could not capture error screenshot:", e.message);
  }
  process.exit(1);
});
