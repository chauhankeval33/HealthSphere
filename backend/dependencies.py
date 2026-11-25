
import logging

from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from backend.database.supabase_client import get_supabase_client


logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    client = get_supabase_client()
    access_token = credentials.credentials

    try:
        # Verify the access token with Supabase Auth.
        response = client.auth.get_user(access_token)

        if response.user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token",
            )

        # Use the authenticated user's JWT for database requests.
        client.postgrest.auth(access_token)

        # Use the authenticated user's JWT for Storage requests.
        storage = client.storage

        storage._headers.update({
            "Authorization": f"Bearer {access_token}"
        })

        storage._client.headers.update({
            "Authorization": f"Bearer {access_token}"
        })

        return {
            "user": response.user,
            "client": client,
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Authentication verification failed"
        )

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
        )
