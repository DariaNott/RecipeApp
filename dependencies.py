from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal

# Імпортуйте ваші класи репозиторію та сервісу (вкажіть правильні шляхи імпорту)
from repos.category_repo import CategoryRepository
from services.category_service import CategoryService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_category_repository(
    db: AsyncSession = Depends(get_db),
) -> CategoryRepository:
    return CategoryRepository(db)


def get_category_service(
    category_repo: CategoryRepository = Depends(get_category_repository),
) -> CategoryService:
    return CategoryService(category_repo)