/**
 * Suppliers domain types mirrored from the backend (source of truth:
 * `backend/app/suppliers/api/schemas.py` and `backend/app/suppliers/domain/constants.py`).
 *
 * Field names are camelCase on this side of the boundary; `src/lib/suppliers/backend.ts`
 * is the only place that maps the API's snake_case shape into these types.
 */

/** BR-SUP lifecycle per docs/03-domain/domain-model.md: prospect -> under_review -> approved|blocked -> inactive. */
export const SUPPLIER_STATUSES = [
  "prospect",
  "under_review",
  "approved",
  "blocked",
  "inactive",
] as const;

export type SupplierStatus = (typeof SUPPLIER_STATUSES)[number];

export const SUPPLIER_STATUS_LABELS: Record<SupplierStatus, string> = {
  prospect: "Prospect",
  under_review: "Under review",
  approved: "Approved",
  blocked: "Blocked",
  inactive: "Inactive",
};

/**
 * Mirrors `ALLOWED_STATUS_TRANSITIONS` in `backend/app/suppliers/domain/constants.py`
 * exactly. Security/QA review (2026-09-29) found the status dropdown offered every other
 * status as a target regardless of the current one, actively inviting a 409 the backend
 * now correctly rejects (e.g. `approved -> prospect`) -- this is a UI-only hint to keep
 * the dropdown honest; the backend's own guard is what's actually authoritative.
 */
export const ALLOWED_STATUS_TRANSITIONS: Record<SupplierStatus, readonly SupplierStatus[]> = {
  prospect: ["under_review", "blocked"],
  under_review: ["approved", "blocked"],
  approved: ["blocked", "inactive"],
  blocked: ["inactive"],
  inactive: [],
};

export interface Supplier {
  id: string;
  organizationId: string;
  legalName: string;
  taxId: string;
  jurisdiction: string;
  status: SupplierStatus;
  createdAt: string;
  updatedAt: string;
}

/** SupplierCheck lifecycle: started -> completed|failed (immutable once settled). */
export const SUPPLIER_CHECK_STATUSES = ["started", "completed", "failed"] as const;

export type SupplierCheckStatus = (typeof SUPPLIER_CHECK_STATUSES)[number];

export const SUPPLIER_CHECK_STATUS_LABELS: Record<SupplierCheckStatus, string> = {
  started: "In progress",
  completed: "Completed",
  failed: "Failed",
};

export interface SupplierCheck {
  id: string;
  supplierId: string;
  status: SupplierCheckStatus;
  sourcesConsulted: string[];
  rawResults: Record<string, unknown>;
  failureReason: string | null;
  startedAt: string;
  completedAt: string | null;
}

/** Normalized `supplier.registry_status` per docs/03-domain/policy-engine.md. */
export type RegistryStatus = "active" | "suspended" | "cancelled" | "unknown";

export const REGISTRY_STATUS_LABELS: Record<RegistryStatus, string> = {
  active: "Active",
  suspended: "Suspended",
  cancelled: "Cancelled",
  unknown: "Unknown",
};

/** Normalized `supplier.address_flag` — a heuristic signal, never a BLOCK-tier rule on its own. */
export type AddressFlag = "consistent" | "flagged" | "unknown";

export const ADDRESS_FLAG_LABELS: Record<AddressFlag, string> = {
  consistent: "Consistent",
  flagged: "Flagged",
  unknown: "Unknown",
};

/**
 * The normalized, current-state SupplierProfile (SUP-003). `sanctionsHit` is
 * BR-SUP-004's compliance-critical signal — every screen showing a profile
 * must treat it as unmissable, never a minor badge among the rest.
 */
export interface SupplierProfile {
  id: string;
  supplierId: string;
  sourceCheckId: string;
  registryStatus: RegistryStatus;
  legalName: string | null;
  corporateStructure: Record<string, unknown>;
  responsibleParties: Array<Record<string, unknown>>;
  cnaeCode: string | null;
  cnaeDescription: string | null;
  address: Record<string, unknown>;
  activityMismatch: boolean;
  addressFlag: AddressFlag;
  sanctionsHit: boolean;
  sanctionsDetail: Array<Record<string, unknown>>;
  createdAt: string;
}
