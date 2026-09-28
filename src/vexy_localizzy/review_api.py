# this_file: src/vexy_localizzy/review_api.py
"""Small local HTTP API over revision-aware filesystem review storage."""

import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from filelock import Timeout
from starlette.middleware.trustedhost import TrustedHostMiddleware

from vexy_localizzy.formats import ts
from vexy_localizzy.qa import TextPolicy
from vexy_localizzy.qa_catalog import check_catalog
from vexy_localizzy.review_api_data import present, select_unit, summary
from vexy_localizzy.review_types import ReviewConflict, ReviewEdit
from vexy_localizzy.translation_types import TranslationExample


def create_app(store, *, ui_files=None, suggestions=None, web_root=None):
    """Only configured catalog/UI IDs are addressable; all writes require revisions."""
    ui_files = dict(ui_files or {})

    def asset(key):
        path = (store.root / ui_files[key]).resolve()
        if not path.is_relative_to(store.root) or path.suffix.lower() != ".ui":
            raise ValueError("UI assets must be .ui files inside the review root")
        return path

    for key in ui_files:
        asset(key)
    app = FastAPI(title="Localizzy review", docs_url=None, redoc_url=None)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"]
    )

    @app.middleware("http")
    async def same_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        if (
            request.method not in ("GET", "HEAD", "OPTIONS")
            and origin
            and origin != str(request.base_url).rstrip("/")
        ):
            return JSONResponse(
                {"detail": "Cross-origin writes are not allowed"}, status_code=403
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    async def missing(_request, _error):
        return JSONResponse({"detail": "Configured item not found"}, status_code=404)

    async def invalid(_request, error):
        return JSONResponse({"detail": str(error)}, status_code=422)

    async def conflict(_request, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

    async def unavailable(_request, _error):
        return JSONResponse(
            {"detail": "Storage unavailable. Reopen before retrying a save."},
            status_code=503,
        )

    for error in (KeyError, FileNotFoundError):
        app.add_exception_handler(error, missing)
    app.add_exception_handler(ValueError, invalid)
    app.add_exception_handler(ReviewConflict, conflict)
    for error in (OSError, Timeout):
        app.add_exception_handler(error, unavailable)

    @app.get("/api/catalogs")
    def catalogs():
        return [summary(key, store.open(key)) for key in store.paths]

    @app.get("/api/catalogs/{catalog_id}")
    def catalog(catalog_id: str):
        return present(catalog_id, store.open(catalog_id))

    @app.post("/api/catalogs/{catalog_id}/edits")
    def save(catalog_id: str, edit: ReviewEdit):
        return present(catalog_id, store.save(catalog_id, edit))

    @app.post("/api/catalogs/{catalog_id}/validate")
    def validate(catalog_id: str, edit: ReviewEdit):
        preview = store.preview(catalog_id, edit)
        findings = check_catalog(
            preview.catalog.model_copy(
                update={"units": [select_unit(preview, edit.key)]}
            ),
            policy=store.policies.get(catalog_id, TextPolicy()),
            required_plural_forms=store.plural_forms.get(catalog_id),
        )
        return {"revision": preview.revision, "findings": findings}

    @app.get("/api/catalogs/{catalog_id}/suggestions")
    def suggest(catalog_id: str, key: str):
        snapshot = store.open(catalog_id)
        unit = select_unit(snapshot, key)
        if unit is None:
            raise HTTPException(status_code=404, detail="Message not found")
        values = suggestions(catalog_id, unit) if suggestions else []
        return [TranslationExample.model_validate(value) for value in values]

    @app.get("/api/catalogs/{catalog_id}/export.ts")
    def export(catalog_id: str):
        snapshot = store.open(catalog_id)
        with tempfile.TemporaryDirectory(prefix="localizzy-review-export-") as work:
            path = Path(work) / "reviewed.ts"
            ts.dump(snapshot.catalog, path)
            raw = path.read_bytes()
        return Response(
            raw,
            media_type="application/xml",
            headers={
                "Content-Disposition": 'attachment; filename="reviewed.ts"',
                "ETag": '"' + snapshot.revision + '"',
            },
        )

    @app.get("/api/ui")
    def assets():
        return [{"id": key, "name": asset(key).name} for key in ui_files]

    @app.get("/api/ui/{asset_id}", response_class=PlainTextResponse)
    def ui(asset_id: str):
        return asset(asset_id).read_text(encoding="utf-8")

    if web_root is not None:
        app.mount("/", StaticFiles(directory=web_root, html=True), name="review")
    return app
