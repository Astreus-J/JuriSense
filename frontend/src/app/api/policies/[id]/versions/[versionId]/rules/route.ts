import { NextResponse } from "next/server";

import { readAccessToken } from "@/lib/auth/cookies";
import { createRule, ApiError } from "@/lib/policies/backend";

interface CreateRuleBody {
  yaml?: unknown;
}

/**
 * BFF endpoint for `RuleForm`'s create mode. Surfaces the backend's 422 (malformed
 * YAML/grammar, `RuleValidationError.message`) and 409 (non-draft version or duplicate
 * rule key) verbatim — both are written to be read by whoever authors the policy.
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string; versionId: string }> },
): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const body = (await request.json().catch(() => null)) as CreateRuleBody | null;
  if (typeof body?.yaml !== "string" || body.yaml.trim().length === 0) {
    return NextResponse.json({ detail: "Rule YAML is required." }, { status: 400 });
  }

  const { id, versionId } = await params;

  try {
    const rule = await createRule(accessToken, id, versionId, body.yaml);
    return NextResponse.json(rule, { status: 201 });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
