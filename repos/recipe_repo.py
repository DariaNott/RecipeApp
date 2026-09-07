import models
import schemas
import math

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, desc, asc
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


    async def get_recipe_links_map(self) -> dict[str, int]:
        result = await self.db.execute(select(models.Recipe.id, models.Recipe.title))
        return {row.title.lower().strip(): row.id for row in result.all()}

    async def get_paginated_list(
        self, page: int = 1, limit: int = 6, category_id: int = None, search_query: str = None, sort: str = "newest"
    ):
        stmt = select(models.Recipe)

        if search_query and search_query.strip():
            q = f"%{search_query.strip()}%"
            stmt = stmt.where(models.Recipe.title.ilike(q) | models.Recipe.description.ilike(q))

        if category_id:
            sub_cats_res = await self.db.execute(
                select(models.Category.id).where(models.Category.parent_id == category_id)
            )
            sub_cat_ids = sub_cats_res.scalars().all()
            target_category_ids = [category_id] + list(sub_cat_ids)
            stmt = stmt.where(models.Recipe.categories.any(models.Category.id.in_(target_category_ids)))

        if sort == "name_asc":
            stmt = stmt.order_by(asc(models.Recipe.title))
        elif sort == "name_desc":
            stmt = stmt.order_by(desc(models.Recipe.title))
        elif sort == "oldest":
            stmt = stmt.order_by(asc(models.Recipe.id))
        else:
            stmt = stmt.order_by(desc(models.Recipe.id))

        # Підрахунок загальної кількості
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total_recipes = count_result.scalar() or 0

        # Пагінація
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)
        recipes_result = await self.db.execute(stmt)
        recipes = recipes_result.scalars().all()

        total_pages = math.ceil(total_recipes / limit) or 1

        pagination = {
            "total": total_recipes,
            "page": page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }

        return recipes, pagination