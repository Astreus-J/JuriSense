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
 * brief), so this stays plain text — e.g. "contract.value.brl (document doc-1, page 2)" or
 * "supplier.sanctions_hit (supplier profile)".
 */
export function describeEvidenceRef(ref: EvidenceRef): string {
  const contextPath = typeof ref.context_path === "string" ? ref.context_path : "Unknown field";
  const source = typeof ref.source === "string" ? ref.source : null;

  if (source === "contract_extracted_field") {
    const documentId = typeof ref.document_id === "string" ? ref.document_id : null;
    const page = typeof ref.page === "number" ? ref.page : null;
    if (documentId && page !== null) return `${contextPath} (document ${documentId}, page ${page})`;
    if (documentId) return `${contextPath} (document ${documentId})`;
    return contextPath;
  }

  if (source === "supplier_profile") {
    return `${contextPath} (supplier profile)`;
  }

  return contextPath;
}
