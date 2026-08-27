from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.services.security import (
    create_access_token,
    hash_password,
    verify_password,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


def set_session_cookie(
    response: RedirectResponse,
    token: str,
) -> None:
    response.set_cookie(
        key="flowforge_session",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60,
        path="/",
    )


@router.post("/register")
def register(
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    full_name = full_name.strip()

    if len(full_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name must contain at least 2 characters.",
        )

    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too long.",
        )

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
    )

    db.add(user)
    db.flush()

    slug_base = (
        full_name
        .lower()
        .strip()
        .replace(" ", "-")
    )

    workspace = Workspace(
        name=f"{full_name}'s Workspace",
        slug=f"{slug_base}-{user.id[:8]}",
    )

    db.add(workspace)
    db.flush()

    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
    )

    db.add(membership)
    db.commit()

    token = create_access_token(user.id)

    response = RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )

    set_session_cookie(response, token)

    return response


@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()

    user = db.scalar(
        select(User).where(User.email == email)
    )

    if not user or not verify_password(
        password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    token = create_access_token(user.id)

    response = RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )

    set_session_cookie(response, token)

    return response


@router.post("/logout")
def logout():
    response = RedirectResponse(
        url="/login",
        status_code=status.HTTP_303_SEE_OTHER,
    )

    response.delete_cookie(
        key="flowforge_session",
        path="/",
    )

    return response