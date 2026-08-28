from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
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
        select(User).where(
            User.id == user_id,
            User.is_active.is_(True),
        )
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is unavailable.",
        )

    return user


def get_current_workspace(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Workspace:
    workspace_id = request.cookies.get("flowforge_workspace")

    membership_query = select(WorkspaceMember).where(
        WorkspaceMember.user_id == user.id
    )

    if workspace_id:
        membership_query = membership_query.where(
            WorkspaceMember.workspace_id == workspace_id
        )

    membership = db.scalar(
        membership_query.order_by(
            WorkspaceMember.created_at.asc()
        )
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No workspace is available for this user.",
        )

    workspace = db.scalar(
        select(Workspace).where(
            Workspace.id == membership.workspace_id
        )
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace is unavailable.",
        )

    return workspace