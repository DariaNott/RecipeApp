from sqlalchemy.ext.asyncio import AsyncSession

import models
import schemas
from sqlalchemy import select


class CategoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[models.Category]:
        stmt = select(models.Category).order_by(models.Category.name.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> models.Category | None:
        stmt = select(models.Category).where(models.Category.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, category_id: int) -> models.Category | None:
        return await self.db.get(models.Category, category_id)

    async def create(self, category_data: schemas.CategoryCreate) -> models.Category:
        new_category = models.Category(
            name=category_data.name,
            parent_id=category_data.parent_id
        )
        self.db.add(new_category)
        await self.db.commit()
        await self.db.refresh(new_category)
        return new_category