from sqlalchemy.ext.asyncio import AsyncSession

import models
import schemas

from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

class RecipeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, recipe_id: int) -> models.Recipe | None:
        return await self.db.get(models.Recipe, recipe_id)

    async def get_by_id_with_details(self, recipe_id: int) -> models.Recipe | None:
        stmt = (
            select(models.Recipe)
            .where(models.Recipe.id == recipe_id)
            .options(
                selectinload(models.Recipe.categories),
                selectinload(models.Recipe.ingredients),
                selectinload(models.Recipe.instructions),
                selectinload(models.Recipe.tips),
            )
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def list_all_with_details(self) -> list[models.Recipe]:
        stmt = (
            select(models.Recipe)
            .options(
                selectinload(models.Recipe.categories),
                selectinload(models.Recipe.ingredients),
                selectinload(models.Recipe.instructions),
                selectinload(models.Recipe.tips),
            )
            .order_by(models.Recipe.id.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def create(self, recipe: models.Recipe) -> models.Recipe:
        self.db.add(recipe)
        await self.db.commit()
        await self.db.refresh(recipe)
        return recipe

    async def delete_by_id(self, recipe_id: int) -> bool:
        recipe = await self.get_by_id(recipe_id)
        if not recipe:
            return False
        await self.db.delete(recipe)
        await self.db.commit()
        return True

    async def commit_and_refresh(self, recipe: models.Recipe) -> models.Recipe:
        await self.db.commit()
        await self.db.refresh(recipe)
        return recipe