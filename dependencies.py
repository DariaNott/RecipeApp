from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal

from repos.category_repo import CategoryRepository
from services.category_service import CategoryService
from repos.recipe_repo import RecipeRepository
from services.recipe_service import RecipeService


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


def get_recipe_repository(
    db: AsyncSession = Depends(get_db),
) -> RecipeRepository:
    return RecipeRepository(db)


def get_recipe_service(
    recipe_repo: RecipeRepository = Depends(get_recipe_repository),
    category_repo: CategoryRepository = Depends(get_category_repository),
) -> RecipeService:
    return RecipeService(recipe_repo, category_repo)