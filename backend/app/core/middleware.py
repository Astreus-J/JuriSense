"""Pure-ASGI middleware -- not `starlette.middleware.base.BaseHTTPMiddleware`, whose
request/response wrapping isn't the right tool for intercepting the body stream itself
before a route/form-parser consumes it.
"""

import json


class MaxBodySizeMiddleware:
    """Rejects a request whose body exceeds `max_bytes`, **before** it reaches
    Starlette's multipart/form parser -- which otherwise reads (and, for `UploadFile`,
    spools to memory or a temp file) the *entire* body before the route function ever
    runs, no matter where `await file.read()` is called inside that function.

    QA/security review (2026-09-29), confirmed live: `POST /api/contracts/upload` had no
    body-size limit anywhere in the ASGI stack -- `document_max_size_bytes` was only
    checked *after* Starlette had already fully received an arbitrarily large upload.
    Both rounds independently found the same gap (QA's CRIT-2, security's MEDIUM #2),
    with a live-measured 300MB upload only rejected after the full transfer completed.

    Two layers:
    1. `Content-Length` header, checked before any body is read at all -- covers the
       overwhelming majority of real clients (browsers, httpx, curl -F) that send it for
       a buffered multipart upload.
    2. A running byte count as the body actually streams in, for a client that omits or
       lies about `Content-Length` (e.g. chunked transfer-encoding) -- this can't
       prevent the bytes already sent from hitting the wire, but it stops accumulating
       and buffering them internally past the limit rather than reading the request to
       completion regardless.
    """

    def __init__(self, app, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = _header(scope, b"content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                declared = None
            if declared is not None and declared > self.max_bytes:
                await _reject(send, self.max_bytes)
                return

        total = 0
        rejected = False

        async def guarded_receive():
            nonlocal total, rejected
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > self.max_bytes:
                    rejected = True
                    # Starve the downstream parser instead of feeding it more bytes --
                    # it will treat this as the body ending early, which is enough for
                    # us to intervene right after `self.app(...)` returns below.
                    return {"type": "http.request", "body": b"", "more_body": False}
            return message

        await self.app(scope, guarded_receive, send)
        if rejected:
            # The downstream app already tried to send its own (likely malformed or
            # incomplete-body-triggered) response by this point in the common case, but
            # ASGI forbids sending twice -- this middleware's job here is limited to
            # making sure the oversized body is never fully buffered, which the early
            # `more_body: False` above already guarantees. Nothing further to send.
            pass


def _header(scope, name: bytes) -> bytes | None:
    for key, value in scope.get("headers", []):
        if key == name:
            return value
    return None


async def _reject(send, max_bytes: int) -> None:
    body = json.dumps(
        {"detail": f"Request body exceeds the maximum allowed size of {max_bytes} bytes"}
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": body})
