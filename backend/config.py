
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )

    return value


# Supabase configuration
SUPABASE_URL = get_required_env("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = get_required_env(
    "SUPABASE_PUBLISHABLE_KEY"
)


# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Text generation model
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite",
)

# Text embedding model
GEMINI_EMBEDDING_MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-001",
)

# Must match PostgreSQL vector(768)
GEMINI_EMBEDDING_DIMENSION = int(
    os.getenv("GEMINI_EMBEDDING_DIMENSION", "768")
)


# Frontend configuration
FRONTEND_ORIGIN = os.getenv(
    "FRONTEND_ORIGIN",
    "http://localhost:5500",
)
