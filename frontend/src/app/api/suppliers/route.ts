import { NextResponse } from "next/server";

import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, createSupplier } from "@/lib/suppliers/backend";

interface CreateSupplierBody {
  legalName?: unknown;
  taxId?: unknown;
  jurisdiction?: unknown;
}

/**
 * BFF endpoint for `CreateSupplierForm`. The browser never holds the access token (it lives
 * in an httpOnly cookie — see `src/lib/auth/cookies.ts`), so any mutation from a Client
 * Component goes through a Route Handler like this one, which reads the cookie server-side
 * and forwards the call with it. Mirrors `src/app/api/session/login/route.ts`'s
 * request-validate / call-backend / unwrap-ApiError shape.
 */
export async function POST(request: Request): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const body = (await request.json().catch(() => null)) as CreateSupplierBody | null;
  if (typeof body?.legalName !== "string" || typeof body?.taxId !== "string") {
    return NextResponse.json(
      { detail: "Legal name and tax ID are required." },
      { status: 400 },
    );
  }
  const jurisdiction =
    typeof body.jurisdiction === "string" && body.jurisdiction.length > 0
      ? body.jurisdiction
      : "BR";

  try {
    const supplier = await createSupplier(accessToken, {
      legalName: body.legalName,
      taxId: body.taxId,
      jurisdiction,
    });
    return NextResponse.json(supplier, { status: 201 });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
