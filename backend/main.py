
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import FRONTEND_ORIGIN

from backend.api.auth import router as auth_router
from backend.api.patients import router as patients_router
from backend.api.documents import router as documents_router
from backend.api.rag import router as rag_router
from backend.api.visit_notes import router as visit_notes_router


# --------------------------------------------------
# Logging configuration
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("healthsphere")


# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="HealthSphere API",
    description="Medical Document AI Assistant",
    version="1.0.0",
)


# --------------------------------------------------
# CORS configuration
# --------------------------------------------------

allowed_origins = list({
    FRONTEND_ORIGIN,
    "http://localhost:5500",
    "http://127.0.0.1:5500",
})

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Global unexpected exception handler
# --------------------------------------------------

@app.exception_handler(Exception)
async def handle_unexpected_exception(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unhandled API exception | Method: %s | Path: %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "An unexpected server error occurred. "
                "Please try again later."
            )
        },
    )


# --------------------------------------------------
# API router registration
# --------------------------------------------------

app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(documents_router)
app.include_router(rag_router)
app.include_router(visit_notes_router)


# --------------------------------------------------
# Root endpoint
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Welcome to HealthSphere API",
        "status": "running",
    }


# --------------------------------------------------
# Health check endpoint
# --------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "HealthSphere",
    }
