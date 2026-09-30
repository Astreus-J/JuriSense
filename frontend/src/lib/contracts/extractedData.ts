/**
 * Pure helpers for walking a `ContractFields` object by the dotted-path format the backend
 * uses for `needs_confirmation_paths` and `ConfirmContractVersionRequest.corrections`
 * (mirrors `backend/app/contracts/domain/extracted_data.py`'s `iter_field_leaves` path
 * shape exactly: `"liability.type"`, `"value.amount"`, `"obligations[0]"`,
 * `"deadlines[2].date"`). No `server-only` import — shared by the read-only detail view
 * (a Server Component) and the confirmation form (a Client Component).
 */

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
 * read raw backend path syntax. */
export function formatFieldPath(path: string): string {
  return parsePath(path)
    .map(({ key, index }) => {
      const label = humanizeKey(key);
      return index !== undefined ? `${label} #${index + 1}` : label;
    })
    .join(" → ");
}
