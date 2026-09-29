import "server-only";

import { ApiError, request } from "@/lib/auth/backend";
import type {
  AddressFlag,
  RegistryStatus,
  Supplier,
  SupplierCheck,
  SupplierCheckStatus,
  SupplierProfile,
  SupplierStatus,
} from "./types";

export { ApiError };

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Security review (2026-09-29): every function below used to interpolate `supplierId`
 * straight into a backend URL path with no validation. Next.js decodes a dynamic route
 * segment (`[id]`) before handing it to a Route Handler, so a request like
 * `PATCH /api/suppliers/..%2Fme/status` arrived here as the literal string `../me`, and
 * `fetch`'s URL parser then resolved that `..` against the backend base URL -- confirmed
 * live to redirect the outbound request (carrying the caller's own bearer token) to an
 * arbitrary backend path (e.g. `/auth/logout`), entirely escaping `/suppliers/{id}` and
 * even the `/api` prefix. The real backend still enforces its own auth/org-scoping on
 * whatever path actually resolves, so no privilege escalation was demonstrated, but this
 * is a confused-deputy primitive that gets more dangerous as more contexts add their own
 * BFF routes reusing this same interpolation pattern. Every backend supplier id actually
 * is a UUID, so reject anything else before it ever reaches a template string.
 */
function assertValidSupplierId(supplierId: string): void {
  if (!UUID_PATTERN.test(supplierId)) {
    throw new ApiError(400, "Invalid supplier id.");
  }
}

/**
 * Thin server-only client for the Suppliers API (`backend/app/suppliers/api/routes.py`),
 * following the exact pattern of `src/lib/auth/backend.ts`: reuse its `request()` helper
 * (base URL resolution, Bearer token, no-store caching, `ApiError` unwrapping) rather than
 * a second HTTP client. Never imported by a Client Component — `server-only` turns an
 * accidental client import into a build error; mutations from Client Components go through
 * the `/api/suppliers/*` Route Handlers instead (tokens live in httpOnly cookies the
 * browser can never read — see `src/lib/auth/cookies.ts`).
 */

interface RawSupplierResponse {
  id: string;
  organization_id: string;
  legal_name: string;
  tax_id: string;
  jurisdiction: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface RawSupplierCheckResponse {
  id: string;
  supplier_id: string;
  status: string;
  sources_consulted: string[];
  raw_results: Record<string, unknown>;
  failure_reason: string | null;
  started_at: string;
  completed_at: string | null;
}

interface RawSupplierProfileResponse {
  id: string;
  supplier_id: string;
  source_check_id: string;
  registry_status: string;
  legal_name: string | null;
  corporate_structure: Record<string, unknown>;
  responsible_parties: Array<Record<string, unknown>>;
  cnae_code: string | null;
  cnae_description: string | null;
  address: Record<string, unknown>;
  activity_mismatch: boolean;
  address_flag: string;
  sanctions_hit: boolean;
  sanctions_detail: Array<Record<string, unknown>>;
  created_at: string;
}

function toSupplier(raw: RawSupplierResponse): Supplier {
  return {
    id: raw.id,
    organizationId: raw.organization_id,
    legalName: raw.legal_name,
    taxId: raw.tax_id,
    jurisdiction: raw.jurisdiction,
    status: raw.status as SupplierStatus,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

function toSupplierCheck(raw: RawSupplierCheckResponse): SupplierCheck {
  return {
    id: raw.id,
    supplierId: raw.supplier_id,
    status: raw.status as SupplierCheckStatus,
    sourcesConsulted: raw.sources_consulted,
    rawResults: raw.raw_results,
    failureReason: raw.failure_reason,
    startedAt: raw.started_at,
    completedAt: raw.completed_at,
  };
}

function toSupplierProfile(raw: RawSupplierProfileResponse): SupplierProfile {
  return {
    id: raw.id,
    supplierId: raw.supplier_id,
    sourceCheckId: raw.source_check_id,
    registryStatus: raw.registry_status as RegistryStatus,
    legalName: raw.legal_name,
    corporateStructure: raw.corporate_structure,
    responsibleParties: raw.responsible_parties,
    cnaeCode: raw.cnae_code,
    cnaeDescription: raw.cnae_description,
    address: raw.address,
    activityMismatch: raw.activity_mismatch,
    addressFlag: raw.address_flag as AddressFlag,
    sanctionsHit: raw.sanctions_hit,
    sanctionsDetail: raw.sanctions_detail,
    createdAt: raw.created_at,
  };
}

export async function listSuppliers(
  accessToken: string,
  status?: SupplierStatus,
): Promise<Supplier[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  const raw = await request<RawSupplierResponse[]>(`/suppliers${query}`, { accessToken });
  return raw.map(toSupplier);
}

export async function getSupplier(accessToken: string, supplierId: string): Promise<Supplier> {
  assertValidSupplierId(supplierId);
  const raw = await request<RawSupplierResponse>(`/suppliers/${supplierId}`, { accessToken });
  return toSupplier(raw);
}

/**
 * Returns `null` on a 404 instead of throwing: per SUP-003, a brand-new supplier whose
 * initial check hasn't completed yet legitimately has no profile — that is "verification
 * in progress," not an error, and callers should render it that way.
 */
export async function getSupplierProfile(
  accessToken: string,
  supplierId: string,
): Promise<SupplierProfile | null> {
  assertValidSupplierId(supplierId);
  try {
    const raw = await request<RawSupplierProfileResponse>(`/suppliers/${supplierId}/profile`, {
      accessToken,
    });
    return toSupplierProfile(raw);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

/** Most recent first — matches the API's own ordering (`SupplierCheckRepository.list_by_supplier`). */
export async function listSupplierChecks(
  accessToken: string,
  supplierId: string,
): Promise<SupplierCheck[]> {
  assertValidSupplierId(supplierId);
  const raw = await request<RawSupplierCheckResponse[]>(`/suppliers/${supplierId}/checks`, {
    accessToken,
  });
  return raw.map(toSupplierCheck);
}

export interface CreateSupplierInput {
  legalName: string;
  taxId: string;
  jurisdiction: string;
}

export async function createSupplier(
  accessToken: string,
  input: CreateSupplierInput,
): Promise<Supplier> {
  const raw = await request<RawSupplierResponse>("/suppliers", {
    method: "POST",
    accessToken,
    body: JSON.stringify({
      legal_name: input.legalName,
      tax_id: input.taxId,
      jurisdiction: input.jurisdiction,
    }),
  });
  return toSupplier(raw);
}

export async function updateSupplierStatus(
  accessToken: string,
  supplierId: string,
  status: SupplierStatus,
): Promise<Supplier> {
  assertValidSupplierId(supplierId);
  const raw = await request<RawSupplierResponse>(`/suppliers/${supplierId}/status`, {
    method: "PATCH",
    accessToken,
    body: JSON.stringify({ status }),
  });
  return toSupplier(raw);
}

/** SUP-002 manual re-check. 202 Accepted — the new SupplierCheck starts `started`, completed asynchronously by Celery. */
export async function recheckSupplier(
  accessToken: string,
  supplierId: string,
): Promise<SupplierCheck> {
  assertValidSupplierId(supplierId);
  const raw = await request<RawSupplierCheckResponse>(`/suppliers/${supplierId}/recheck`, {
    method: "POST",
    accessToken,
  });
  return toSupplierCheck(raw);
}
