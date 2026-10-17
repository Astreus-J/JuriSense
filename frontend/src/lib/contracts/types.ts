/**
 * Contracts & Documents domain types mirrored from the backend (source of truth:
 * `backend/app/contracts/api/schemas.py` and `backend/app/contracts/domain/constants.py`).
 *
 * `Contract`/`ContractVersion`/`Clause` follow the same camelCase convention as
 * `lib/suppliers/types.ts` — `lib/contracts/backend.ts` is the only place that maps the
 * API's snake_case shape into these types.
 *
 * `ExtractedData`/`ContractFields` are the one exception: they mirror
 * `backend/app/ai_services/domain/schema.py`'s `ContractFields` *as a structural
 * pass-through*, keys unchanged, the same way `SupplierProfile.corporateStructure`/
 * `address` stay in their original shape — this is a deeply-nested, schema-defined JSON
 * blob (`docs/05-ai/structured-extraction.md`), not a flat API resource, and re-keying
 * every nested leaf to camelCase would multiply mapping code for no behavioral benefit.
 * Display code formats keys for humans at render time (see `formatFieldPath` in
 * `./extractedData.ts`), the same pattern `SupplierProfileCard.formatKey` already uses.
 */

export const CONTRACT_STATUSES = [
  "draft",
  "under_review",
  "active",
  "renewed",
  "terminated",
  "expired",
] as const;

export type ContractStatus = (typeof CONTRACT_STATUSES)[number];

export interface Contract {
  id: string;
  organizationId: string;
  supplierId: string;
  title: string;
  contractType: string;
  status: ContractStatus;
  createdAt: string;
  updatedAt: string;
}

/**
 * Per `backend/app/contracts/domain/constants.py`'s `ContractVersionStatus` docstring:
 * `extracted` is the version's *initial* state, written the instant it's created and
 * before the async AI extraction has even run — `extracted_data` is still `{}` and
 * `extraction_confidence` is still `null` at that point. It is a transient "processing"
 * state, never a terminal one; screens must not treat it as "extraction complete with no
 * data." Once the Celery task finishes, it becomes either `needs_confirmation` (any field
 * below the confidence threshold, BR-CON-003) or `analyzed` (every field met it), or
 * `extraction_failed` if the AI Gateway/parsing step itself failed.
 */
export const CONTRACT_VERSION_STATUSES = [
  "extracted",
  "needs_confirmation",
  "analyzed",
  "extraction_failed",
] as const;

export type ContractVersionStatus = (typeof CONTRACT_VERSION_STATUSES)[number];

/** The universal leaf wrapper every extracted fact is stored in (`ExtractedValue` in
 * `schema.py`). `human_confirmed`/`human_corrected` are stamped by CON-005's confirmation
 * flow (`apply_confirmation`) and absent until then. */
export interface ExtractedLeaf<T = unknown> {
  value: T;
  confidence: number;
  provenance: {
    document_id: string;
    page: number;
    text_span: { start: number; end: number };
  };
  human_confirmed?: boolean;
  human_corrected?: boolean;
}

export interface ContractParty {
  role: string;
  name: string;
  tax_id?: string | null;
}

export interface ContractDeadline {
  description: string;
  date?: ExtractedLeaf<string> | null;
}

/** Structural mirror of `ContractFields` (`schema.py`) — see the module docstring above
 * for why keys stay snake_case. Every leaf is optional: a contract may simply not mention
 * a given term. */
export interface ContractFields {
  contract_type?: ExtractedLeaf<string> | null;
  parties?: ExtractedLeaf<ContractParty[]> | null;
  value?: {
    amount?: ExtractedLeaf<number> | null;
    currency?: ExtractedLeaf<string> | null;
  };
  duration?: {
    start_date?: ExtractedLeaf<string> | null;
    end_date?: ExtractedLeaf<string> | null;
    auto_renewal?: ExtractedLeaf<boolean> | null;
  };
  termination?: {
    notice_period_days?: ExtractedLeaf<number> | null;
    termination_for_convenience?: ExtractedLeaf<boolean> | null;
    termination_for_cause_conditions?: ExtractedLeaf<string> | null;
  };
  liability?: {
    type?: ExtractedLeaf<string> | null;
    cap?: ExtractedLeaf<string | number> | null;
  };
  privacy?: {
    processes_personal_data?: ExtractedLeaf<boolean> | null;
    dpa_present?: ExtractedLeaf<boolean> | null;
  };
  obligations?: ExtractedLeaf<string>[];
  subprocessors?: ExtractedLeaf<string>[];
  jurisdiction?: ExtractedLeaf<string> | null;
  guarantees?: ExtractedLeaf<string>[];
  penalties?: ExtractedLeaf<string>[];
  deadlines?: ContractDeadline[];
}

export interface ExtractedData {
  extraction_run_id: string;
  model: { provider: string; model_name: string; prompt_version: string };
  extracted_at: string;
  pagination_mode: string;
  fields: ContractFields;
}

export interface ContractVersion {
  id: string;
  contractId: string;
  documentId: string;
  versionNumber: number;
  status: ContractVersionStatus;
  /** `{}` while `status === "extracted"` (extraction hasn't produced data yet) or when
   * `status === "extraction_failed"`. */
  extractedData: ExtractedData | Record<string, never>;
  extractionConfidence: number | null;
  extractionFailureReason: string | null;
  createdAt: string;
  /** Dotted paths into `extractedData.fields` (e.g. `"liability.type"`) that are below
   * the confidence threshold and not yet human-confirmed — see `needs_confirmation_paths`
   * on `ContractVersionResponse`. Always `[]` outside `needs_confirmation`. */
  needsConfirmationPaths: string[];
}

export interface Clause {
  id: string;
  contractVersionId: string;
  clauseType: string;
  page: number;
  textSpan: { start: number; end: number };
  confidence: number;
  textExcerpt: string | null;
}
