import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy import text
from src.backend.db.connection import engine
from src.backend.db.init_db import init_database, seed_demo_data
from src.backend.api.v1.auth import router as auth_router
from src.backend.api.v1.patients import router as patients_router
from src.backend.api.v1.documents import router as documents_router
from src.backend.api.v1.ai import router as ai_router
from src.backend.api.v1.extraction import router as extraction_router
from src.backend.api.v1.timeline import router as timeline_router
from src.backend.api.v1.intelligence import router as intelligence_router
from src.backend.api.v1.summaries import router as summaries_router
from src.backend.api.v1.drafts import router as drafts_router

# Load environment variables from .env if present
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is ready on startup
    init_database()
    # Seed fictional demo accounts for local development and demonstration
    # Can be disabled in production deployments via SKIP_DEMO_SEED=true
    if os.getenv("SKIP_DEMO_SEED", "").lower() not in ("1", "true", "yes"):
        seed_demo_data()
    yield



app = FastAPI(
    title="MedBrief AI API",
    description="Medical Report Summarisation Assistant - Backend API",
    version="0.1.0",
    lifespan=lifespan,
)

# Register API routers
app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(documents_router)
app.include_router(ai_router)
app.include_router(extraction_router)
app.include_router(timeline_router)
app.include_router(intelligence_router)
app.include_router(summaries_router)
app.include_router(drafts_router)

# Configure CORS with strict allowed origins
cors_env = os.getenv("CORS_ORIGINS", "")
if cors_env.strip():
    allowed_origins = [o.strip() for o in cors_env.split(",") if o.strip()]
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {
        "status": "ok",
        "app": "MedBrief AI",
        "version": "0.1.0",
        "environment": os.getenv("APP_ENV", "development"),
    }


@app.get("/health")
def health_check():
    db_status = "healthy"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        # Sanitize error to avoid leaking credentials or connection strings
        db_status = "unhealthy: database connectivity failure"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "backend",
        "database": db_status,
    }


@app.get("/ready")
def readiness_check():
    db_ready = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ready = False

    return {
        "status": "ready" if db_ready else "not_ready",
        "service": "backend",
        "database": "connected" if db_ready else "disconnected",
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", os.getenv("APP_PORT", "8000")))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("src.backend.main:app", host=host, port=port, reload=False)



