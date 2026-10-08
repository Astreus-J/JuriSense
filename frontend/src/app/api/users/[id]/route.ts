import { NextResponse } from "next/server";

import { isRole } from "@/lib/auth/types";
import type { Role } from "@/lib/auth/types";
import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, deactivateUser, updateUser } from "@/lib/organization/backend";
import { USER_STATUSES } from "@/lib/organization/types";
import type { UserStatus } from "@/lib/organization/types";

interface UpdateUserBody {
  fullName?: unknown;
  phone?: unknown;
  role?: unknown;
  status?: unknown;
}

function isUserStatus(value: unknown): value is UserStatus {
  return typeof value === "string" && (USER_STATUSES as readonly string[]).includes(value);
}

/**
 * BFF endpoint for `TeamMemberActions`'s role-change control. Surfaces the backend's 400
 * (`OperationNotAllowedError` — e.g. an admin changing their own role) and 402
 * (`UserLimitReachedError` — reactivating a user past the plan's seat limit) verbatim.
 * Mirrors `/api/suppliers/[id]/status/route.ts`'s shape.
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
  const body = (await request.json().catch(() => null)) as UpdateUserBody | null;
  if (!body) {
    return NextResponse.json({ detail: "A request body is required." }, { status: 400 });
  }

  const update: {
    fullName?: string;
    phone?: string;
    role?: Role;
    status?: UserStatus;
  } = {};

  if (typeof body.fullName === "string") update.fullName = body.fullName;
  if (typeof body.phone === "string") update.phone = body.phone;
  if (body.role !== undefined) {
    if (typeof body.role !== "string" || !isRole(body.role)) {
      return NextResponse.json({ detail: "Invalid role." }, { status: 400 });
    }
    update.role = body.role;
  }
  if (body.status !== undefined) {
    if (!isUserStatus(body.status)) {
      return NextResponse.json({ detail: "Invalid status." }, { status: 400 });
    }
    update.status = body.status;
  }

  if (Object.keys(update).length === 0) {
    return NextResponse.json({ detail: "No fields to update." }, { status: 400 });
  }

  try {
    const member = await updateUser(accessToken, id, update);
    return NextResponse.json(member);
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}

/**
 * BFF endpoint for `TeamMemberActions`'s deactivate control. Logical deactivation, not a
 * hard delete (see `deactivateUser`'s doc comment) — surfaces the backend's 400
 * (`OperationNotAllowedError` — an admin can't deactivate their own account) verbatim.
 */
export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const { id } = await params;

  try {
    await deactivateUser(accessToken, id);
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
