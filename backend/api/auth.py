
import logging

from fastapi import APIRouter, Depends, HTTPException
from supabase import create_client

from backend.config import (
    SUPABASE_URL,
    SUPABASE_PUBLISHABLE_KEY,
)

from backend.schemas.auth import SignupRequest, LoginRequest
from backend.dependencies import get_current_user


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


def get_auth_client():
    return create_client(
        SUPABASE_URL,
        SUPABASE_PUBLISHABLE_KEY,
    )


@router.post("/signup")
def signup(data: SignupRequest):
    try:
        client = get_auth_client()

        response = client.auth.sign_up({
            "email": data.email,
            "password": data.password,
        })

        logger.info("Signup request processed successfully")

        return {
            "message": (
                "Signup request submitted. "
                "Check your email if verification is required."
            ),
            "user_id": response.user.id if response.user else None,
            "email_confirmation_required": response.session is None,
        }

    except Exception:
        logger.exception("Signup request failed")

        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to complete signup. "
                "Please check your details or try again later."
            ),
        )


@router.post("/login")
def login(data: LoginRequest):
    try:
        client = get_auth_client()

        response = client.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password,
        })

        if not response.session or not response.user:
            logger.warning("Login returned without a valid session")

            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
            )

        logger.info("User login successful")

        return {
            "message": "Login successful",
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "bearer",
            "user": {
                "id": response.user.id,
                "email": response.user.email,
            },
        }

    except HTTPException:
        raise

    except Exception:
        logger.warning("Login attempt failed")

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )


@router.get("/me")
def get_profile(context=Depends(get_current_user)):
    user = context["user"]

    return {
        "id": user.id,
        "email": user.email,
    }
