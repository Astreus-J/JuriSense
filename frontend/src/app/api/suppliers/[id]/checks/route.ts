import { NextResponse } from "next/server";

import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, listSupplierChecks } from "@/lib/suppliers/backend";

/**
 * #142: `SupplierDetailActions`'s recheck button polls this to find out whether the
 * Celery task it just started later settled as `completed` or `failed` -- the 202 from
 * `POST .../recheck` only confirms the check *started*, not how it turned out.
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const { id } = await params;

  try {
    const checks = await listSupplierChecks(accessToken, id);
    return NextResponse.json(checks);
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
