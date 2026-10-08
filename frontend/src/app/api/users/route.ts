import { NextResponse } from "next/server";

import { isRole } from "@/lib/auth/types";
import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, createUser } from "@/lib/organization/backend";

interface CreateUserBody {
  fullName?: unknown;
  email?: unknown;
  password?: unknown;
  role?: unknown;
  phone?: unknown;
}

/**
 * BFF endpoint for `POST /users` (direct admin-created account, as opposed to
 * `InviteUserForm`'s email-invite flow at `/api/users/invites`, which is this screen's
 * primary path for adding teammates). Mirrors `/api/suppliers/route.ts`'s shape exactly.
 */
export async function POST(request: Request): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const body = (await request.json().catch(() => null)) as CreateUserBody | null;
  if (
    typeof body?.fullName !== "string" ||
    typeof body?.email !== "string" ||
    typeof body?.password !== "string" ||
    typeof body?.role !== "string" ||
    !isRole(body.role)
  ) {
    return NextResponse.json(
      { detail: "Full name, email, password, and a valid role are required." },
      { status: 400 },
    );
  }
  const phone = typeof body.phone === "string" && body.phone.length > 0 ? body.phone : undefined;

  try {
    const member = await createUser(accessToken, {
      fullName: body.fullName,
      email: body.email,
      password: body.password,
      role: body.role,
      phone,
    });
    return NextResponse.json(member, { status: 201 });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
