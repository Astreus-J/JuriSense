import { NextResponse } from "next/server";

import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, updateRule } from "@/lib/policies/backend";

interface UpdateRuleBody {
  yaml?: unknown;
}

/** BFF endpoint for `RuleForm`'s edit mode. Same error-shape contract as the create route. */
export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string; versionId: string; ruleId: string }> },
): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const body = (await request.json().catch(() => null)) as UpdateRuleBody | null;
  if (typeof body?.yaml !== "string" || body.yaml.trim().length === 0) {
    return NextResponse.json({ detail: "Rule YAML is required." }, { status: 400 });
  }

  const { id, versionId, ruleId } = await params;

  try {
    const rule = await updateRule(accessToken, id, versionId, ruleId, body.yaml);
    return NextResponse.json(rule);
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
