from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.crm import router as crm_router
from app.api.leads import router as leads_router
from app.api.operations import router as operations_router

from app.config import settings
from app.web import router as web_router


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered business automation platform",
)


app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)


app.include_router(auth_router)
app.include_router(crm_router)
app.include_router(leads_router)
app.include_router(operations_router)
app.include_router(web_router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "application": settings.app_name,
        "version": settings.app_version,
    }