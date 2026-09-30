import { NextResponse } from "next/server";

import { readAccessToken } from "@/lib/auth/cookies";
import { ApiError, uploadContractVersion } from "@/lib/contracts/backend";

function stringField(value: FormDataEntryValue | null): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

// Mirrors backend/app/core/config.py's document_max_size_bytes (25 MB) plus the same
// multipart-overhead margin backend/app/core/middleware.py's MaxBodySizeMiddleware uses.
const MAX_UPLOAD_BYTES = 25_000_000 + 65_536;

class BodyTooLargeError extends Error {}

/**
 * QA/security review (2026-09-30), confirmed live: a `Content-Length` pre-check alone
 * (what this route had before) is a no-op against a chunked-transfer-encoded request --
 * verified live that Next.js still buffered the full body proportional to its actual
 * size before this route's own check ever ran, the exact two-layer gap
 * `backend/app/core/middleware.py`'s `MaxBodySizeMiddleware` was built to close on the
 * backend (its own docstring: "a `Content-Length`... check... can't prevent [a client
 * that lies/omits it]"). This counts bytes as the body actually streams through, aborting
 * before more than `maxBytes` is ever buffered -- mirrors that middleware's second layer,
 * one level up, in the BFF itself rather than the FastAPI app.
 */
function capRequestBody(request: Request, maxBytes: number): Request {
  if (!request.body) return request;
  let total = 0;
  const limited = request.body.pipeThrough(
    new TransformStream<Uint8Array, Uint8Array>({
      transform(chunk, controller) {
        total += chunk.byteLength;
        if (total > maxBytes) {
          controller.error(new BodyTooLargeError());
          return;
        }
        controller.enqueue(chunk);
      },
    }),
  );
  return new Request(request.url, {
    method: request.method,
    headers: request.headers,
    body: limited,
    // Required by undici/fetch whenever a Request body is a stream, not a static value.
    duplex: "half",
  } as RequestInit & { duplex: "half" });
}

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

  let formData: FormData;
  try {
    formData = await capRequestBody(request, MAX_UPLOAD_BYTES).formData();
  } catch (error) {
    if (error instanceof BodyTooLargeError) {
      return NextResponse.json(
        { detail: `Request body exceeds the maximum allowed size of ${MAX_UPLOAD_BYTES} bytes` },
        { status: 413 },
      );
    }
    return NextResponse.json({ detail: "Could not read the upload." }, { status: 400 });
  }
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
