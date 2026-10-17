/**
 * Pure helpers for walking a `ContractFields` object by the dotted-path format the backend
 * uses for `needs_confirmation_paths` and `ConfirmContractVersionRequest.corrections`
 * (mirrors `backend/app/contracts/domain/extracted_data.py`'s `iter_field_leaves` path
 * shape exactly: `"liability.type"`, `"value.amount"`, `"obligations[0]"`,
 * `"deadlines[2].date"`). No `server-only` import — shared by the read-only detail view
 * (a Server Component) and the confirmation form (a Client Component).
 */

import type { MessageKey, Translator } from "@/lib/i18n/translate";
import type { ExtractedLeaf } from "./types";

interface PathSegment {
  key: string;
  index?: number;
}

function parsePath(path: string): PathSegment[] {
  return path.split(".").map((token) => {
    const match = /^([^[]+)(?:\[(\d+)\])?$/.exec(token);
    if (!match) return { key: token };
    const [, key, index] = match;
    return { key, index: index !== undefined ? Number(index) : undefined };
  });
}

function isLeafShaped(node: unknown): node is ExtractedLeaf {
  return (
    typeof node === "object" &&
    node !== null &&
    "value" in node &&
    "confidence" in node &&
    "provenance" in node
  );
}

/** Resolves a dotted path against a `ContractFields`-shaped object. Returns `undefined`
 * when the path doesn't resolve to a well-formed leaf (missing field, stale path from a
 * prior version, etc.) rather than throwing — callers render nothing for that case. */
export function getLeafAtPath(fields: unknown, path: string): ExtractedLeaf | undefined {
  let node: unknown = fields;
  for (const { key, index } of parsePath(path)) {
    if (typeof node !== "object" || node === null) return undefined;
    node = (node as Record<string, unknown>)[key];
    if (index !== undefined) {
      if (!Array.isArray(node)) return undefined;
      node = node[index];
    }
  }
  return isLeafShaped(node) ? node : undefined;
}

function humanizeKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

/** `"liability.type"` -> `"Liability → Type"`, `"deadlines[2].date"` -> `"Deadlines #3 →
 * Date"`. Used to label a field in the confirmation flow without the reviewer needing to
 * read raw backend path syntax. Each segment is looked up in `contracts.segments.*`; an
 * unknown segment (a field the backend adds before the catalogs learn about it) falls back
 * to the humanized raw key. */
export function formatFieldPath(path: string, { t }: Translator): string {
  return parsePath(path)
    .map(({ key, index }) => {
      const messageKey = `contracts.segments.${key}`;
      const translated = t(messageKey as MessageKey);
      const label = translated === messageKey ? humanizeKey(key) : translated;
      return index !== undefined ? `${label} #${index + 1}` : label;
    })
    .join(" → ");
}

export type LeafType = "boolean" | "number" | "string" | "object";

/**
 * QA review (2026-09-30): the confirmation form used to dispatch its input type on
 * `typeof leaf.value`, which breaks for every nullable leaf whose AI-extracted `value` is
 * `null` — a documented, legitimate, and specifically *likely* case for exactly the
 * low-confidence fields this form handles. `typeof null === "object"` is excluded by the
 * `!== null` guard, so a null boolean/number field fell through to a plain text input,
 * and a typed correction like "true" was submitted as the literal string `"true"`, not
 * `true` — silently corrupting the field's type for every downstream consumer (the future
 * Policy Engine's normalized context expects real booleans/numbers, per
 * `docs/05-ai/structured-extraction.md`'s mapping table).
 *
 * `ExtractedValue.value` is typed `Any` at the Pydantic level (`app/ai_services/domain
 * /schema.py`) — nothing server-side constrains it either, so this map is the one place
 * that encodes each field's *intended* type from `structured-extraction.md`'s own
 * `extractedBoolean`/`extractedNumber`/`extractedString` annotations, keyed by path with
 * array indices stripped (`"obligations[3]"` -> `"obligations"`,
 * `"deadlines[1].date"` -> `"deadlines.date"`).
 */
const LEAF_TYPE_BY_NORMALIZED_PATH: Record<string, LeafType> = {
  contract_type: "string",
  parties: "object",
  "value.amount": "number",
  "value.currency": "string",
  "duration.start_date": "string",
  "duration.end_date": "string",
  "duration.auto_renewal": "boolean",
  "termination.notice_period_days": "number",
  "termination.termination_for_convenience": "boolean",
  "termination.termination_for_cause_conditions": "string",
  "liability.type": "string",
  "liability.cap": "number",
  "privacy.processes_personal_data": "boolean",
  "privacy.dpa_present": "boolean",
  obligations: "string",
  subprocessors: "string",
  jurisdiction: "string",
  guarantees: "string",
  penalties: "string",
  "deadlines.date": "string",
};

export function expectedTypeForPath(path: string): LeafType {
  const normalized = path.replace(/\[\d+\]/g, "");
  return LEAF_TYPE_BY_NORMALIZED_PATH[normalized] ?? "string";
}
