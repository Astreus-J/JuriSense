import { NextResponse } from "next/server";

import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, confirmContractVersion } from "@/lib/contracts/backend";

interface ConfirmBody {
  corrections?: unknown;
}

/** BFF endpoint for `ConfirmationForm`'s submit (CON-005/BR-CON-003). */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string; versionId: string }> },
): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const { id, versionId } = await params;
  const body = (await request.json().catch(() => null)) as ConfirmBody | null;
  const corrections =
    body && typeof body.corrections === "object" && body.corrections !== null
      ? (body.corrections as Record<string, unknown>)
      : {};

  try {
    const version = await confirmContractVersion(accessToken, id, versionId, corrections);
    return NextResponse.json(version, { status: 200 });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
