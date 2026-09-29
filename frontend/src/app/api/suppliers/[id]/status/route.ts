import { NextResponse } from "next/server";

import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, updateSupplierStatus } from "@/lib/suppliers/backend";
import { SUPPLIER_STATUSES } from "@/lib/suppliers/types";
import type { SupplierStatus } from "@/lib/suppliers/types";

function isSupplierStatus(value: unknown): value is SupplierStatus {
  return typeof value === "string" && (SUPPLIER_STATUSES as readonly string[]).includes(value);
}

/**
 * BFF endpoint for `SupplierDetailActions`'s status-change control. Surfaces the backend's
 * 409 (BR-SUP-003 — approving without a clean completed check) verbatim so the UI can show
 * the actual reason for the rejection.
 */
export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const { id } = await params;
  const body = (await request.json().catch(() => null)) as { status?: unknown } | null;
  if (!isSupplierStatus(body?.status)) {
    return NextResponse.json({ detail: "A valid status is required." }, { status: 400 });
  }

  try {
    const supplier = await updateSupplierStatus(accessToken, id, body.status);
    return NextResponse.json(supplier);
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
