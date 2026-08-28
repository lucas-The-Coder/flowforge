from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.security import decode_access_token
from app.services.workspace_auth import get_current_workspace
from app.templates import templates


router = APIRouter()


def get_browser_user(
    request: Request,
    db: Session,
) -> User | None:
    token = request.cookies.get("flowforge_session")

    if not token:
        return None

    user_id = decode_access_token(token)

    if not user_id:
        return None

    return db.scalar(
        select(User).where(
            User.id == user_id,
            User.is_active.is_(True),
        )
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "title": "Login",
        },
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "title": "Register",
        },
    )


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_browser_user(request, db)

    if user is None:
        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    workspace = get_current_workspace(
        request=request,
        db=db,
        user=user,
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "title": "Dashboard",
            "user": user,
            "workspace": workspace,
        },
    )