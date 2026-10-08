import "server-only";

import { ApiError, request } from "@/lib/auth/backend";
import type {
  CreatePolicyResult,
  Policy,
  PolicyStatus,
  PolicyVersion,
  PolicyVersionStatus,
  Rule,
  RuleResultStatus,
  Severity,
} from "./types";

export { ApiError };

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Same guard as `lib/suppliers/backend.ts`'s `assertValidSupplierId` (see that function's
 * docstring for the confirmed-live confused-deputy bug this prevents), applied to every
 * id this module interpolates into a backend URL path (`policyId`/`versionId`/`ruleId`).
 * Every backend id here is a UUID; reject anything else before it ever reaches a template
 * string.
 */
function assertValidId(id: string, label: string): void {
  if (!UUID_PATTERN.test(id)) {
    throw new ApiError(400, `Invalid ${label}.`);
  }
}

/**
 * Thin server-only client for the Policy & Compliance API
 * (`backend/app/policies/api/routes.py`), following `lib/suppliers/backend.ts`'s exact
 * pattern. Never imported by a Client Component — `server-only` turns an accidental
 * client import into a build error; mutations from Client Components go through the
 * `/api/policies/*` Route Handlers instead (tokens live in httpOnly cookies the browser
 * can never read).
 */

interface RawPolicyResponse {
  id: string;
  organization_id: string;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface RawPolicyVersionResponse {
  id: string;
  policy_id: string;
  version_number: number;
  status: string;
  is_current: boolean;
  published_at: string | null;
  published_by: string | null;
  created_at: string;
}

interface RawRuleResponse {
  id: string;
  policy_version_id: string;
  rule_key: string;
  name: string;
  when: Record<string, unknown>;
  result_status: string;
  severity: string;
  approver_role: string | null;
  compiled_presence_cel: string;
  compiled_condition_cel: string;
  is_frozen: boolean;
  created_at: string;
  updated_at: string;
}

function toPolicy(raw: RawPolicyResponse): Policy {
  return {
    id: raw.id,
    organizationId: raw.organization_id,
    name: raw.name,
    status: raw.status as PolicyStatus,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

function toPolicyVersion(raw: RawPolicyVersionResponse): PolicyVersion {
  return {
    id: raw.id,
    policyId: raw.policy_id,
    versionNumber: raw.version_number,
    status: raw.status as PolicyVersionStatus,
    isCurrent: raw.is_current,
    publishedAt: raw.published_at,
    publishedBy: raw.published_by,
    createdAt: raw.created_at,
  };
}

function toRule(raw: RawRuleResponse): Rule {
  return {
    id: raw.id,
    policyVersionId: raw.policy_version_id,
    ruleKey: raw.rule_key,
    name: raw.name,
    when: raw.when,
    resultStatus: raw.result_status as RuleResultStatus,
    severity: raw.severity as Severity,
    approverRole: raw.approver_role,
    compiledPresenceCel: raw.compiled_presence_cel,
    compiledConditionCel: raw.compiled_condition_cel,
    isFrozen: raw.is_frozen,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

export async function listPolicies(accessToken: string): Promise<Policy[]> {
  const raw = await request<RawPolicyResponse[]>("/policies", { accessToken });
  return raw.map(toPolicy);
}

export async function createPolicy(
  accessToken: string,
  name: string,
): Promise<CreatePolicyResult> {
  const raw = await request<{
    policy: RawPolicyResponse;
    initial_version: RawPolicyVersionResponse;
  }>("/policies", {
    method: "POST",
    accessToken,
    body: JSON.stringify({ name }),
  });
  return {
    policy: toPolicy(raw.policy),
    initialVersion: toPolicyVersion(raw.initial_version),
  };
}

export async function getPolicy(accessToken: string, policyId: string): Promise<Policy> {
  assertValidId(policyId, "policy id");
  const raw = await request<RawPolicyResponse>(`/policies/${policyId}`, { accessToken });
  return toPolicy(raw);
}

export async function listPolicyVersions(
  accessToken: string,
  policyId: string,
): Promise<PolicyVersion[]> {
  assertValidId(policyId, "policy id");
  const raw = await request<RawPolicyVersionResponse[]>(`/policies/${policyId}/versions`, {
    accessToken,
  });
  return raw.map(toPolicyVersion);
}

/** BR-POL-001's copy-modify path: a new draft version, its rules copied from the current
 * published version (if any). No conflict if a draft already exists — the service always
 * creates one at the next version number regardless (see `policy_service.create_draft_version`). */
export async function createDraftVersion(
  accessToken: string,
  policyId: string,
): Promise<PolicyVersion> {
  assertValidId(policyId, "policy id");
  const raw = await request<RawPolicyVersionResponse>(`/policies/${policyId}/versions`, {
    method: "POST",
    accessToken,
  });
  return toPolicyVersion(raw);
}

export async function getPolicyVersion(
  accessToken: string,
  policyId: string,
  versionId: string,
): Promise<PolicyVersion> {
  assertValidId(policyId, "policy id");
  assertValidId(versionId, "policy version id");
  const raw = await request<RawPolicyVersionResponse>(
    `/policies/${policyId}/versions/${versionId}`,
    { accessToken },
  );
  return toPolicyVersion(raw);
}

/** Freezes every Rule in this version (BR-POL-001) and makes it the Policy's one current
 * version (BR-POL-002). 409 if the version isn't a draft, or on a concurrent-publish race. */
export async function publishPolicyVersion(
  accessToken: string,
  policyId: string,
  versionId: string,
): Promise<PolicyVersion> {
  assertValidId(policyId, "policy id");
  assertValidId(versionId, "policy version id");
  const raw = await request<RawPolicyVersionResponse>(
    `/policies/${policyId}/versions/${versionId}/publish`,
    { method: "POST", accessToken },
  );
  return toPolicyVersion(raw);
}

export async function listRules(
  accessToken: string,
  policyId: string,
  versionId: string,
): Promise<Rule[]> {
  assertValidId(policyId, "policy id");
  assertValidId(versionId, "policy version id");
  const raw = await request<RawRuleResponse[]>(
    `/policies/${policyId}/versions/${versionId}/rules`,
    { accessToken },
  );
  return raw.map(toRule);
}

export async function getRule(
  accessToken: string,
  policyId: string,
  versionId: string,
  ruleId: string,
): Promise<Rule> {
  assertValidId(policyId, "policy id");
  assertValidId(versionId, "policy version id");
  assertValidId(ruleId, "rule id");
  const raw = await request<RawRuleResponse>(
    `/policies/${policyId}/versions/${versionId}/rules/${ruleId}`,
    { accessToken },
  );
  return toRule(raw);
}

/** `yaml` is the raw rule DSL text (ADR-004: authors interact with YAML, never raw
 * CEL/JSONLogic). 409 on a non-draft version or a duplicate rule key; 422 with the real
 * validation message on malformed YAML/grammar — surfaced verbatim by the caller. */
export async function createRule(
  accessToken: string,
  policyId: string,
  versionId: string,
  yaml: string,
): Promise<Rule> {
  assertValidId(policyId, "policy id");
  assertValidId(versionId, "policy version id");
  const raw = await request<RawRuleResponse>(
    `/policies/${policyId}/versions/${versionId}/rules`,
    { method: "POST", accessToken, body: JSON.stringify({ yaml }) },
  );
  return toRule(raw);
}

export async function updateRule(
  accessToken: string,
  policyId: string,
  versionId: string,
  ruleId: string,
  yaml: string,
): Promise<Rule> {
  assertValidId(policyId, "policy id");
  assertValidId(versionId, "policy version id");
  assertValidId(ruleId, "rule id");
  const raw = await request<RawRuleResponse>(
    `/policies/${policyId}/versions/${versionId}/rules/${ruleId}`,
    { method: "PUT", accessToken, body: JSON.stringify({ yaml }) },
  );
  return toRule(raw);
}
