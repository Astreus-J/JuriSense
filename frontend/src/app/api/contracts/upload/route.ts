import { NextResponse } from "next/server";

import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, uploadContractVersion } from "@/lib/contracts/backend";

function stringField(value: FormDataEntryValue | null): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

// Mirrors backend/app/core/config.py's document_max_size_bytes (25 MB) plus the same
// multipart-overhead margin backend/app/core/middleware.py's MaxBodySizeMiddleware uses.
// Found during review (2026-09-30): request.formData() below fully buffers the request
// body into the Next.js server's memory before any of this route's own code runs --
// Next.js App Router Route Handlers have no built-in body-size cap (unlike the old Pages
// API's bodyParser.sizeLimit), so without this check an oversized upload hits the exact
// same unbounded-buffering issue the backend's MaxBodySizeMiddleware was added to fix,
// just one layer up, in the BFF itself rather than the FastAPI app.
const MAX_UPLOAD_BYTES = 25_000_000 + 65_536;

/**
 * BFF endpoint for `UploadContractForm`. `multipart/form-data` in, `multipart/form-data`
 * (via `requestMultipart`) out to the real backend — the browser never holds the access
 * token (httpOnly cookie, see `src/lib/auth/cookies.ts`), same pattern as
 * `src/app/api/suppliers/route.ts` but for a file upload instead of a JSON body.
 */
export async function POST(request: Request): Promise<Response> {
  const accessToken = await readAccessToken();
  if (!accessToken) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }

  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (declaredLength > MAX_UPLOAD_BYTES) {
    return NextResponse.json(
      { detail: `Request body exceeds the maximum allowed size of ${MAX_UPLOAD_BYTES} bytes` },
      { status: 413 },
    );
  }

  const formData = await request.formData();
  const file = formData.get("file");
  const supplierId = stringField(formData.get("supplierId"));

  if (!(file instanceof File) || file.size === 0) {
    return NextResponse.json({ detail: "A contract document is required." }, { status: 400 });
  }
  if (!supplierId) {
    return NextResponse.json({ detail: "A supplier is required." }, { status: 400 });
  }

  try {
    const version = await uploadContractVersion(accessToken, {
      file,
      supplierId,
      contractId: stringField(formData.get("contractId")),
      title: stringField(formData.get("title")),
      contractType: stringField(formData.get("contractType")),
    });
    return NextResponse.json(version, { status: 201 });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ detail: error.detail }, { status: error.status });
    }
    return NextResponse.json({ detail: "Unexpected error." }, { status: 500 });
  }
}
