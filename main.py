from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("🚀 Database initiated successfully!")
    yield

app = FastAPI(
    title="My Recipes",
    version="1.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")

from routers.web import router as web_router
from routers.admin import router as admin_router

app.include_router(web_router)
app.include_router(admin_router)

@app.get("/api", tags=["Root"])
async def root():
    return {
        "status": "working",
        "message": "Welcome to Recipe Management API. Go to /docs for Swagger UI documentation."
    }