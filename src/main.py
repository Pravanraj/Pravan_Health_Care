"""Main FastAPI Application Entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.database.connection import init_db
from src.api.auth_router import router as auth_router
from src.api.patient_router import router as patient_router
from src.api.encounter_router import router as encounter_router
from src.api.analytics_router import router as analytics_router
from src.api.report_router import router as report_router
from src.api.etl_router import router as etl_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan hook: initialize database schema and seed default users."""
    init_db()
    yield


app = FastAPI(
    title="Healthcare Patient Management System API",
    description="Enterprise microservice for clinical patient management, ETL ingestion, operational KPIs, and readmission analytics.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local Streamlit frontend and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register versioned API routers under /api/v1
app.include_router(auth_router, prefix="/api/v1")
app.include_router(patient_router, prefix="/api/v1")
app.include_router(encounter_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(report_router, prefix="/api/v1")
app.include_router(etl_router, prefix="/api/v1")


@app.get("/", tags=["System"])
def root():
    """System status and API overview."""
    return {
        "system": "Healthcare Patient Management System",
        "status": "online",
        "version": "1.0.0",
        "documentation": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint for liveness and readiness probes."""
    return {"status": "healthy"}
