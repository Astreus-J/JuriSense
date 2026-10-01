/**
 * Pure helper for rendering one `EvidenceRef` as a plain-text SOURCE citation — the only
 * place in the frontend that reads an evidence ref's (snake_case) keys, mirroring how
 * `lib/contracts/extractedData.ts`'s helpers are the one place that walks `ContractFields`.
 * No `server-only` import — shared by server-rendered components only today, but nothing
 * here depends on a secret or a server-only API.
 */

import type { EvidenceRef } from "./types";

/**
 * `context_path` (e.g. `"contract.value.brl"` or `"supplier.sanctions_hit"`) is always
 * present and is a legitimate citation on its own (persona: "Evidence should be directly
 * connected to conclusions"). When the richer fields are present, add the document/page or
 * supplier-profile context. No document viewer exists yet (out of scope per this story's
 * brief), so this stays plain text — e.g. "contract.value.brl (document doc-1, page 2,
 * chars 120-145)" or "supplier.sanctions_hit (supplier profile)".
 */
export function describeEvidenceRef(ref: EvidenceRef): string {
  const contextPath = typeof ref.context_path === "string" ? ref.context_path : "Unknown field";
  const source = typeof ref.source === "string" ? ref.source : null;

  if (source === "contract_extracted_field") {
    const documentId = typeof ref.document_id === "string" ? ref.document_id : null;
    const page = typeof ref.page === "number" ? ref.page : null;
    // QA review (2026-10-01): the backend computes a character-offset `text_span` for every
    // contract-sourced ref specifically as part of this feature's WHY/EVIDENCE/POLICY/SOURCE
    // explainability goal — it was being read into `EvidenceRef` but never rendered, silently
    // dropping the most precise SOURCE citation available.
    const textSpan =
      ref.text_span &&
      typeof ref.text_span === "object" &&
      typeof (ref.text_span as Record<string, unknown>).start === "number" &&
      typeof (ref.text_span as Record<string, unknown>).end === "number"
        ? (ref.text_span as { start: number; end: number })
        : null;

    const parts: string[] = [];
    if (documentId) parts.push(`document ${documentId}`);
    if (page !== null) parts.push(`page ${page}`);
    if (textSpan) parts.push(`chars ${textSpan.start}-${textSpan.end}`);

    return parts.length > 0 ? `${contextPath} (${parts.join(", ")})` : contextPath;
  }

  if (source === "supplier_profile") {
    return `${contextPath} (supplier profile)`;
  }

  return contextPath;
}
