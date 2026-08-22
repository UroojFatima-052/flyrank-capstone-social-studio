from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import create_db_and_tables
from app.routers import campaigns, posts, schedule, variants

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

app.include_router(posts.router)
app.include_router(campaigns.router)
app.include_router(variants.router)
app.include_router(schedule.router)

@app.get("/health")
def health():
    return {"status": "ok"}