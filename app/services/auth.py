from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.security import decode_access_token


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = request.cookies.get("flowforge_session")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    user_id = decode_access_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )

    user = db.scalar(
        select(User).where(User.id == user_id)
    )

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is unavailable.",
        )

    return user


def get_browser_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = request.cookies.get("flowforge_session")

    if not token:
        from fastapi.responses import RedirectResponse

        raise BrowserAuthenticationRequired


class BrowserAuthenticationRequired(Exception):
    pass