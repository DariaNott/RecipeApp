from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///instance/recipes.db"

# TODO change engine when migrated to postgreSQL
# SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg://postgres:test1234!@localhost/RecipeAppDatabase"

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_async_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL)

# Створюємо фабрику асинхронних сесій
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

Base = declarative_base()


# Cyrillic Fix
@event.listens_for(engine.sync_engine, "connect")
def setup_sqlite_functions(dbapi_connection, connection_record):
    if hasattr(dbapi_connection, "create_function"):
        dbapi_connection.create_function("py_lower", 1, lambda s: s.lower() if s else s)
