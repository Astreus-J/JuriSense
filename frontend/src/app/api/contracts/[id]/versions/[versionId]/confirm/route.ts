import { NextResponse } from "next/server";

import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, confirmContractVersion } from "@/lib/contracts/backend";

interface ConfirmBody {
  corrections?: unknown;
}

// Security review (2026-09-30): `corrections` is arbitrary client-supplied JSON with no
// size bound before this route buffers/parses it. Lower-risk than the upload route (JSON
// bodies here are inherently small in the legitimate case, and the backend's own
// MaxBodySizeMiddleware still applies once forwarded), but a consistent guard regardless.
const MAX_BODY_BYTES = 1_000_000;

/** BFF endpoint for `ConfirmationForm`'s submit (CON-005/BR-CON-003). */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string; versionId: string }> },
): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (declaredLength > MAX_BODY_BYTES) {
    return NextResponse.json(
      { detail: `Request body exceeds the maximum allowed size of ${MAX_BODY_BYTES} bytes` },
      { status: 413 },
    );
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
