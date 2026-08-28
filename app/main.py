from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.services.security import decode_access_token
from app.services.workspace_auth import get_current_workspace


BASE_DIR = Path(__file__).resolve().parent


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered business automation platform",
)


app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)


templates = Jinja2Templates(
    directory=BASE_DIR / "templates",
)


app.include_router(auth_router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "application": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "title": "Login",
        },
    )


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "title": "Register",
        },
    )


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


@app.get("/", response_class=HTMLResponse)
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