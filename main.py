from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Автоматичне створення таблиць у базі даних
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("🚀 Database initiated successfully!")
    yield

# 1. Створюємо екземпляр додатку FastAPI
app = FastAPI(
    title="My Recipes",
    version="1.0.0",
    lifespan=lifespan
)

# 2. Монтуємо статику
app.mount("/static", StaticFiles(directory="static"), name="static")

# 3. Імпортуємо роутери ПІСЛЯ створення app та налаштування статики
from routers.web import router as web_router
from routers.admin import router as admin_router

# 4. Підключаємо роутери в додаток
app.include_router(web_router)
app.include_router(admin_router)

@app.get("/api", tags=["Root"])
async def root():
    return {
        "status": "working",
        "message": "Welcome to Recipe Management API. Go to /docs for Swagger UI documentation."
    }