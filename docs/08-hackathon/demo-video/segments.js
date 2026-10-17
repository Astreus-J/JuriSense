// Single source of truth for the demo video: narration text (-> espeak audio + captions)
// and which UI action happens during each segment (-> Playwright script).
// Narration text matches docs/08-hackathon/demo-video-script.md verbatim (trimmed of
// bracketed [ACTION:] cues, which live in `action` below instead).

module.exports = [
  {
    id: "intro",
    action: "login-as-admin",
    narration:
      "This is JuriSense Gate. It turns contracts, supplier data, and company policies into " +
      "auditable compliance decisions. Acme Tecnologia, a two hundred person Brazilian SaaS " +
      "company, needs to hire a new vendor. This organization and its compliance policy were " +
      "configured ahead of time. What you are about to see is the live supplier and contract " +
      "workflow.",
  },
  {
    id: "supplier-create",
    action: "create-supplier",
    narration:
      "First, the supplier. I create CloudDocs Software as a new supplier, using its tax I.D. " +
      "It starts in prospect status.",
  },
  {
    id: "supplier-check",
    action: "view-supplier-check",
    narration:
      "Submitting the tax I.D. triggers a supplier check, a point in time verification against " +
      "official sources: company registry status, and the sanctions lists. This check is " +
      "immutable once it completes. We never overwrite a verification run, we create a new one.",
  },
  {
    id: "contract-upload-v1",
    action: "upload-contract-v1",
    narration:
      "Now the contract. I upload Cloud Docs' proposed SaaS agreement. On upload, the system " +
      "computes a SHA two fifty six hash of the document. This is what eventually chains into " +
      "the Evidence Package.",
  },
  {
    id: "extraction-wait",
    action: "wait-extraction",
    narration: "A.I. extraction is running against the contract now.",
  },
  {
    id: "extraction-result",
    action: "view-extraction",
    narration:
      "And here are the extracted terms. Contract value, four hundred eighty thousand reais a " +
      "year. Term, twenty four months. Unlimited liability. It processes personal data, yes. A " +
      "Data Processing Agreement, absent. Every one of these fields traces back to a specific " +
      "clause in the source document. This is provenance, not a black box summary.",
  },
  {
    id: "compliance-review-v1",
    action: "trigger-review",
    narration:
      "Now I trigger a compliance review against Acme's published policy.",
  },
  {
    id: "compliance-result-v1",
    action: "view-review-block",
    narration:
      "Three rules fired. L.G.P.D. zero zero one: the contract processes personal data but has " +
      "no D.P.A., that's a BLOCK, critical severity. LEGAL zero zero eight: unlimited liability, " +
      "REVIEW. FIN zero zero three: contract value over the threshold, REVIEW. Here's the " +
      "product's core explainability claim: even though two rules only said REVIEW, one rule " +
      "said BLOCK, and BLOCK always wins, because it's the safer failure mode.",
  },
  {
    id: "contract-upload-v2",
    action: "upload-contract-v2",
    narration:
      "CloudDocs corrects the contract. They add a D.P.A. and cap liability. This is a brand " +
      "new contract version, never an edit to the old one, which stays exactly as it was.",
  },
  {
    id: "extraction-wait-v2",
    action: "wait-extraction-v2",
    narration: "A.I. extraction runs again on the corrected version.",
  },
  {
    id: "compliance-review-v2",
    action: "trigger-review-v2",
    narration: "A new compliance review runs against the same published policy.",
  },
  {
    id: "compliance-result-v2",
    action: "view-review-review",
    narration:
      "L.G.P.D. zero zero one now passes. Liability is no longer unlimited. But FIN zero zero " +
      "three still fires, the contract value hasn't changed. Aggregation now yields REVIEW, not " +
      "APPROVE. This is realistic, not a scripted everything turns green moment. A R. four " +
      "hundred eighty thousand, twenty four month contract still needs a human legal sign off " +
      "on value alone, even after the compliance blocker is fixed.",
  },
  {
    id: "approval",
    action: "approve-as-legal",
    narration:
      "Because this is REVIEW, an approval request routes to whoever holds the Legal role in " +
      "this organization, not a hardcoded person. Logged in as Acme's Legal approver, I see the " +
      "full rationale, and I approve it, with a justification note.",
  },
  {
    id: "passport",
    action: "view-passport",
    narration:
      "With the decision resolved, the system packages a Decision Passport: the decision, the " +
      "supplier, the contract, document hashes, the exact policy version evaluated, every rule " +
      "evaluation, including the historical BLOCK, the A.I.'s own execution provenance, the " +
      "approver, and the timestamp. Ask why was this approved, two years from now, and this is " +
      "the complete, reproducible answer.",
  },
  {
    id: "anchor-note",
    action: "none",
    narration:
      "A note here: the blockchain anchor for this decision was pre submitted a few minutes " +
      "before this recording. Constellation's network needs time to reach consensus, so we " +
      "don't sit here waiting on camera. Only the next step, verify, is live.",
  },
  {
    id: "verify-open",
    action: "open-verify",
    narration:
      "Last step, the public verification page. No login required. That's the whole point of a " +
      "public, third party checkable proof.",
  },
  {
    id: "verify-click",
    action: "click-verify",
    narration:
      "I click Verify, live, right now. And it confirms the hash matches what was anchored. " +
      "Anyone, an auditor, a regulator, an acquirer's due diligence team, can independently " +
      "confirm this decision's evidence hasn't been tampered with, without trusting JuriSense's " +
      "word for it.",
  },
  {
    id: "close",
    action: "none",
    narration:
      "That's JuriSense Gate. Contracts, supplier data, and company policies, turned into " +
      "auditable compliance decisions.",
  },
];
