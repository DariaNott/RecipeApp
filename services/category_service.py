import models
import schemas
from repos.category_repo import CategoryRepository
from fastapi import HTTPException, status



class CategoryService:
    def __init__(self, category_repo: CategoryRepository):
        self.category_repo = category_repo

    async def get_all_categories(self) -> list[models.Category]:
        return await self.category_repo.get_all()

    async def create_category(self, category_data: schemas.CategoryCreate) -> models.Category:
        if await self.category_repo.get_by_name(category_data.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with name '{category_data.name}' already exists."
            )

        if category_data.parent_id is not None:
            parent = await self.category_repo.get_by_id(category_data.parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Parent category with ID {category_data.parent_id} not found."
                )

        return await self.category_repo.create(category_data)