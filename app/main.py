from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Social Media Studio",
    description="Turns one blog post into a scheduled multi-platform social campaign.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ok"}