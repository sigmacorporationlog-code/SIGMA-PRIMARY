from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
import uuid
from time import perf_counter
from app.services.observability import record_request, set_request_id, reset_request_id, normalize_request_id, install_logging_context
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.paths import static_dir
from app.api import honor_board, auth, users, students, academic, finance, organization, dashboard, cards, communication, communication_v3, reports, evaluation, system, sync, notifications, search, cloud, legal, billing_v4, ai, ai_actions, ai_knowledge, parent, teacher, onboarding, operations_v4, performance, payment_gateway, sla, fleet, pilot, backup_cloud, public_documents

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "SIGMA — Système Intégré de Gestion et Management Académique.\n\n"
        "API REST du serveur central SIGMA (MVP): Administration, Élèves, "
        "Académique, Finance, Cartes, Communication, Rapports, Pilotage."
    ),
)

if settings.GZIP_ENABLED:
    app.add_middleware(GZipMiddleware, minimum_size=max(256, settings.GZIP_MINIMUM_SIZE))

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(organization.router)
app.include_router(users.router)
app.include_router(students.router)
app.include_router(academic.router)
app.include_router(honor_board.router)
app.include_router(evaluation.router)
app.include_router(finance.router)
app.include_router(cards.router)
app.include_router(communication.router)
app.include_router(communication_v3.router)
app.include_router(reports.router)
app.include_router(dashboard.router)
app.include_router(system.router)
app.include_router(sync.router)
app.include_router(notifications.router)
app.include_router(search.router)
app.include_router(cloud.router)
app.include_router(legal.router)
app.include_router(billing_v4.router)
app.include_router(ai.router)
app.include_router(ai_actions.router)
app.include_router(ai_knowledge.router)
app.include_router(parent.router)
app.include_router(teacher.router)
app.include_router(onboarding.router)
app.include_router(operations_v4.router)
app.include_router(performance.router)
app.include_router(payment_gateway.router)
app.include_router(sla.router)
app.include_router(fleet.router)
app.include_router(pilot.router)
app.include_router(backup_cloud.router)
app.include_router(public_documents.router)

app.mount("/dashboard", StaticFiles(directory=str(static_dir()), html=True), name="dashboard")


def _i18n_dir():
    from app.core.version import _candidate_paths
    for manifest in _candidate_paths():
        candidate = manifest.parent / "i18n"
        if candidate.exists():
            return candidate
    return Path(__file__).resolve().parents[1] / "i18n"


app.mount("/i18n", StaticFiles(directory=str(_i18n_dir()), html=False), name="i18n")


@app.on_event("startup")
def ensure_media_directories() -> None:
    install_logging_context()
    if settings.ENV.lower() == "production" and not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY doit être définie en production")
    import app.models  # noqa
    from app.services.backup import apply_pending_restore
    apply_pending_restore()
    from app.services.upgrade import apply_pending_upgrade
    apply_pending_upgrade()
    from app.core.database import Base, engine, ensure_schema_compatibility
    bootstrap_envs = {"development", "test", "pilot"}
    if settings.ENV.lower() in bootstrap_envs:
        Base.metadata.create_all(bind=engine)
        ensure_schema_compatibility()

    
    from app.services.media import media_root

    (media_root() / "students").mkdir(parents=True, exist_ok=True)


@app.get("/", tags=["Santé"])
def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "v3_version": settings.V3_VERSION,
        "status": "en ligne",
        "dashboard": "/dashboard/",
        "documentation": "/docs",
    }


@app.get("/api/health", tags=["Santé"])
def health():
    return {"status": "ok", "version": settings.V3_VERSION}


@app.get("/api/version", tags=["Santé"])
def version_info():
    """Version publique non sensible utilisée par les clients offline/synchronisés."""
    return {"product": settings.APP_NAME, "version": settings.APP_VERSION, "channel": settings.RELEASE_CHANNEL}


@app.get("/api/health/live", tags=["Santé"])
def health_live():
    return {"status": "alive"}


@app.get("/api/health/ready", tags=["Santé"])
def health_ready():
    from app.services.production import readiness
    result = readiness(None)
    return JSONResponse(status_code=200 if result["status"] == "ready" else 503, content=result)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = normalize_request_id(request.headers.get(settings.REQUEST_ID_HEADER))
    token = set_request_id(request_id)
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        record_request(request.method, request.url.path, 500, (perf_counter() - started) * 1000, request_id=request_id)
        reset_request_id(token)
        raise
    record_request(request.method, request.url.path, response.status_code, (perf_counter() - started) * 1000, request_id=request_id)
    response.headers[settings.REQUEST_ID_HEADER] = request_id
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    # P1 CSP: all networked content remains same-origin. `unsafe-inline` is
    # retained temporarily because the current static frontend embeds legacy
    # inline scripts/styles and handlers; `unsafe-eval` is deliberately absent.
    csp = (
        "default-src 'self'; "
        "base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; "
        "script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' blob: data:; font-src 'self' data:; connect-src 'self'; "
        "manifest-src 'self'; worker-src 'self' blob:; frame-src 'none'"
    )
    if settings.ENV.lower() == "production": csp += "; upgrade-insecure-requests"
    response.headers.setdefault("Content-Security-Policy", csp)
    if settings.ENV.lower() == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    reset_request_id(token)
    return response
