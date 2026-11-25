
from supabase import Client, create_client

from backend.config import (
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY,
)


def get_supabase_client() -> Client:
    """
    Create and return a Supabase client.
    """

    client = create_client(
        SUPABASE_URL,
        SUPABASE_PUBLISHABLE_KEY,
    )

    return client


# Shared Supabase client
supabase = get_supabase_client()
