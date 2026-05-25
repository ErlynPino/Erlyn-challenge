import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from app.config import settings
from app.database import engine
from app.routers import users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up")
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("DB tables verified/created")
    except Exception as exc:
        logger.warning("DB table creation skipped: %s", exc)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "RESTful API for user management with full CRUD operations. "
        "Interactive docs available at **/docs** (Swagger UI) and **/redoc**."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)


@app.get("/health", tags=["health"], summary="Health check")
def health_check() -> dict:
    return {"status": "ok", "version": settings.app_version}
