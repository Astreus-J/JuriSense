import { NextResponse } from "next/server";

import { isRole } from "@/lib/auth/types";
import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, createInvite, listInvites } from "@/lib/organization/backend";

interface CreateInviteBody {
  email?: unknown;
  role?: unknown;
  fullName?: unknown;
}

/**
 * BFF endpoint for `InviteUserForm`. Distinct from `/api/session/accept-invite` (the
 * invitee-side flow that consumes a token to set a password) — this is the admin-side action
 * that creates the invitation in the first place. Resending to the same email cancels the
 * previous pending invitation (`invite_service.invite_user`'s own docstring), so a second
 * call for the same address is a normal 201, not a 409.
 */
export async function POST(request: Request): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const body = (await request.json().catch(() => null)) as CreateInviteBody | null;
  if (
    typeof body?.email !== "string" ||
    typeof body?.role !== "string" ||
    !isRole(body.role)
  ) {
    return NextResponse.json(
      { detail: "A valid email and role are required." },
      { status: 400 },
    );
  }
  const fullName =
    typeof body.fullName === "string" && body.fullName.length > 0 ? body.fullName : undefined;

  try {
    const invitation = await createInvite(accessToken, { email: body.email, role: body.role, fullName });
    return NextResponse.json(invitation, { status: 201 });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}

/**
 * Not used by `OrganizationSettingsPage` today (a Server Component, it calls `listInvites`
 * directly — same stance as `/api/compliance/reviews/[id]/route.ts`'s GET), but included for
 * parity with every other list endpoint in this app in case a future Client Component needs
 * to re-fetch without a full page refresh.
 */
export async function GET(): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  try {
    const invitations = await listInvites(accessToken);
    return NextResponse.json(invitations);
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
