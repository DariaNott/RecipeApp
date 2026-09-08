from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from typing import List

import schemas
from dependencies import get_recipe_service, get_category_service
from services.category_service import CategoryService
from services.recipe_service import RecipeService

router = APIRouter(prefix="/api/v1/admin", tags=["Admin CRUD API"])

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

SECRET_API_KEY = "my_super_secret_recipe_app_key_123"


async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != SECRET_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key is invalid. Access denied."
        )
    return api_key


@router.get("/recipes/", response_model=List[schemas.RecipeDetailResponse])
async def admin_get_recipes(
        recipe_service: RecipeService = Depends(get_recipe_service),
        _=Depends(verify_api_key)
):
    return await recipe_service.get_all_recipes()


@router.get("/recipes/{recipe_id}", response_model=schemas.RecipeDetailResponse)
async def admin_get_recipe_by_id(
        recipe_id: int,
        recipe_service: RecipeService = Depends(get_recipe_service),
        _=Depends(verify_api_key)
):
    return await recipe_service.get_recipe_by_id(recipe_id)


@router.post("/recipes/", response_model=schemas.RecipeDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe(
        recipe_data: schemas.RecipeCreate,
        recipe_service: RecipeService = Depends(get_recipe_service),
        _=Depends(verify_api_key)
):
    return await recipe_service.create_recipe(recipe_data)


@router.put("/recipes/{recipe_id}", response_model=schemas.RecipeDetailResponse)
async def update_recipe(
        recipe_id: int,
        recipe_data: schemas.RecipeCreate,
        recipe_service: RecipeService = Depends(get_recipe_service),
        _=Depends(verify_api_key)
):
    return await recipe_service.update_recipe(recipe_id, recipe_data)


@router.delete("/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
        recipe_id: int,
        recipe_service: RecipeService = Depends(get_recipe_service),
        _=Depends(verify_api_key)
):
    await recipe_service.delete_recipe(recipe_id)
    return None


@router.get("/categories/", response_model=list[schemas.CategoryResponse], status_code=status.HTTP_200_OK)
async def get_all_categories(
        category_service: CategoryService = Depends(get_category_service),
        _=Depends(verify_api_key)
):
    return await category_service.get_all_categories()


@router.post("/categories/", response_model=schemas.CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
        category_data: schemas.CategoryCreate,
        category_service: CategoryService = Depends(get_category_service),
        _=Depends(verify_api_key)
):
    return await category_service.create_category(category_data)
