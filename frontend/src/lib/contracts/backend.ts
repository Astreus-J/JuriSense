import "server-only";

import { ApiError, request, requestMultipart } from "@/lib/auth/backend";
import type {
  Clause,
  Contract,
  ContractStatus,
  ContractVersion,
  ContractVersionStatus,
  ExtractedData,
} from "./types";

export { ApiError };

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Same guard as `lib/suppliers/backend.ts`'s `assertValidSupplierId`, applied to every id
 * this module interpolates into a backend URL path (`contractId`/`versionId`) — see that
 * function's docstring for the confirmed-live confused-deputy bug (commit `555a8e5`) this
 * exists to prevent. Every backend id here is a UUID; reject anything else before it ever
 * reaches a template string.
 */
function assertValidId(id: string, label: string): void {
  if (!UUID_PATTERN.test(id)) {
    throw new ApiError(400, `Invalid ${label}.`);
  }
}

/**
 * Thin server-only client for the Contracts API (`backend/app/contracts/api/routes.py`),
 * following `lib/suppliers/backend.ts`'s exact pattern. Never imported by a Client
 * Component — `server-only` turns an accidental client import into a build error;
 * mutations from Client Components go through the `/api/contracts/*` Route Handlers
 * instead (tokens live in httpOnly cookies the browser can never read).
 */

interface RawContractResponse {
  id: string;
  organization_id: string;
  supplier_id: string;
  title: string;
  contract_type: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface RawContractVersionResponse {
  id: string;
  contract_id: string;
  document_id: string;
  version_number: number;
  status: string;
  extracted_data: Record<string, unknown>;
  extraction_confidence: number | null;
  extraction_failure_reason: string | null;
  created_at: string;
  needs_confirmation_paths: string[];
}

interface RawClauseResponse {
  id: string;
  contract_version_id: string;
  clause_type: string;
  page: number;
  text_span: { start: number; end: number };
  confidence: number;
  text_excerpt: string | null;
}

function toContract(raw: RawContractResponse): Contract {
  return {
    id: raw.id,
    organizationId: raw.organization_id,
    supplierId: raw.supplier_id,
    title: raw.title,
    contractType: raw.contract_type,
    status: raw.status as ContractStatus,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

function toContractVersion(raw: RawContractVersionResponse): ContractVersion {
  return {
    id: raw.id,
    contractId: raw.contract_id,
    documentId: raw.document_id,
    versionNumber: raw.version_number,
    status: raw.status as ContractVersionStatus,
    // Structural pass-through (see lib/contracts/types.ts's module docstring) -- `{}`
    // while `extracted`/`extraction_failed`, otherwise the full `ExtractedData` shape.
    extractedData: raw.extracted_data as unknown as ExtractedData | Record<string, never>,
    extractionConfidence: raw.extraction_confidence,
    extractionFailureReason: raw.extraction_failure_reason,
    createdAt: raw.created_at,
    needsConfirmationPaths: raw.needs_confirmation_paths,
  };
}

function toClause(raw: RawClauseResponse): Clause {
  return {
    id: raw.id,
    contractVersionId: raw.contract_version_id,
    clauseType: raw.clause_type,
    page: raw.page,
    textSpan: raw.text_span,
    confidence: raw.confidence,
    textExcerpt: raw.text_excerpt,
  };
}

export async function listContracts(accessToken: string): Promise<Contract[]> {
  const raw = await request<RawContractResponse[]>("/contracts", { accessToken });
  return raw.map(toContract);
}

export async function getContract(accessToken: string, contractId: string): Promise<Contract> {
  assertValidId(contractId, "contract id");
  const raw = await request<RawContractResponse>(`/contracts/${contractId}`, { accessToken });
  return toContract(raw);
}

/** Most recent negotiation round last — matches the API's own ordering
 * (`ContractVersionRepository.list_by_contract`, ascending `version_number`). */
export async function listContractVersions(
  accessToken: string,
  contractId: string,
): Promise<ContractVersion[]> {
  assertValidId(contractId, "contract id");
  const raw = await request<RawContractVersionResponse[]>(`/contracts/${contractId}/versions`, {
    accessToken,
  });
  return raw.map(toContractVersion);
}

export async function getContractVersion(
  accessToken: string,
  contractId: string,
  versionId: string,
): Promise<ContractVersion> {
  assertValidId(contractId, "contract id");
  assertValidId(versionId, "contract version id");
  const raw = await request<RawContractVersionResponse>(
    `/contracts/${contractId}/versions/${versionId}`,
    { accessToken },
  );
  return toContractVersion(raw);
}

/** CON-004: every clause carries its page/span citation (BR-CON-004). */
export async function listContractVersionClauses(
  accessToken: string,
  contractId: string,
  versionId: string,
): Promise<Clause[]> {
  assertValidId(contractId, "contract id");
  assertValidId(versionId, "contract version id");
  const raw = await request<RawClauseResponse[]>(
    `/contracts/${contractId}/versions/${versionId}/clauses`,
    { accessToken },
  );
  return raw.map(toClause);
}

export interface UploadContractVersionInput {
  file: File;
  supplierId: string;
  /** Omit to create a brand-new `Contract`; provide to add a new negotiation-round
   * version to an existing one (BR-CON-002). */
  contractId?: string;
  /** Required only when `contractId` is omitted. */
  title?: string;
  contractType?: string;
}

/** CON-001/CON-002. `multipart/form-data`, unlike every other Contracts endpoint — see
 * `requestMultipart`'s docstring in `lib/auth/backend.ts` for why this can't reuse
 * `request()`. */
export async function uploadContractVersion(
  accessToken: string,
  input: UploadContractVersionInput,
): Promise<ContractVersion> {
  if (input.contractId) assertValidId(input.contractId, "contract id");

  const formData = new FormData();
  formData.set("file", input.file);
  formData.set("supplier_id", input.supplierId);
  if (input.contractId) formData.set("contract_id", input.contractId);
  if (input.title) formData.set("title", input.title);
  if (input.contractType) formData.set("contract_type", input.contractType);

  const raw = await requestMultipart<RawContractVersionResponse>("/contracts/upload", {
    accessToken,
    formData,
  });
  return toContractVersion(raw);
}

/** CON-005/BR-CON-003: confirms a `needs_confirmation` `ContractVersion`, unblocking it to
 * `analyzed`. `corrections` maps a dotted field path to a human-corrected value; omit a
 * path (or send `{}`) to accept that field's AI value as-is. */
export async function confirmContractVersion(
  accessToken: string,
  contractId: string,
  versionId: string,
  corrections: Record<string, unknown>,
): Promise<ContractVersion> {
  assertValidId(contractId, "contract id");
  assertValidId(versionId, "contract version id");
  const raw = await request<RawContractVersionResponse>(
    `/contracts/${contractId}/versions/${versionId}/confirm`,
    { method: "POST", accessToken, body: JSON.stringify({ corrections }) },
  );
  return toContractVersion(raw);
}
