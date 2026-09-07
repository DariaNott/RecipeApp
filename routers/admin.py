from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List

import models
import schemas
from dependencies import *
from services.category_service import CategoryService

router = APIRouter(prefix="/api/v1/admin", tags=["Admin CRUD API"])

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

SECRET_API_KEY = "my_super_secret_recipe_app_key_123"


async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != SECRET_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Невірний або відсутній API Ключ"
        )
    return api_key


@router.get("/recipes/", response_model=List[schemas.RecipeDetailResponse])
async def admin_get_recipes(
        db: AsyncSession = Depends(get_db),
        _=Depends(verify_api_key)
):
    stmt = (
        select(models.Recipe)
        .options(
            selectinload(models.Recipe.categories),
            selectinload(models.Recipe.ingredients),
            selectinload(models.Recipe.instructions),
            selectinload(models.Recipe.tips)
        )
        .order_by(models.Recipe.id.desc())
    )
    result = await db.execute(stmt)
    return result.unique().scalars().all()


@router.get("/recipes/{recipe_id}", response_model=schemas.RecipeDetailResponse)
async def admin_get_recipe_by_id(
        recipe_id: int,
        db: AsyncSession = Depends(get_db),
        _=Depends(verify_api_key)
):
    stmt = (
        select(models.Recipe)
        .where(models.Recipe.id == recipe_id)
        .options(
            selectinload(models.Recipe.categories),
            selectinload(models.Recipe.ingredients),
            selectinload(models.Recipe.instructions),
            selectinload(models.Recipe.tips)
        )
    )

    result = await db.execute(stmt)
    recipe = result.unique().scalar_one_or_none()

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Рецепт з ID {recipe_id} не знайдено"
        )

    return recipe


@router.post("/recipes/", response_model=schemas.RecipeDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe(
        recipe_data: schemas.RecipeCreate,
        db: AsyncSession = Depends(get_db),
        _=Depends(verify_api_key)
):
    assigned_categories = []
    if recipe_data.category_names:
        for cat_name in recipe_data.category_names:
            stmt = select(models.Category).where(models.Category.name == cat_name)
            result = await db.execute(stmt)
            category = result.scalar_one_or_none()

            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Категорію з назвою '{cat_name}' не знайдено. Створіть її спочатку."
                )
            assigned_categories.append(category)

    assigned_ingredients = []
    if recipe_data.ingredients:
        for ing in recipe_data.ingredients:
            assigned_ingredients.append(
                models.RecipeIngredient(name=ing.name, amount=ing.amount)
            )

    assigned_instructions = []
    if recipe_data.instructions:
        for step in recipe_data.instructions:
            assigned_instructions.append(
                models.RecipeInstruction(step=step.step, text=step.text)
            )

    assigned_tips = []
    if recipe_data.tips:
        for tip in recipe_data.tips:
            assigned_tips.append(
                models.RecipeTip(text=tip.text)
            )

    new_recipe = models.Recipe(
        title=recipe_data.title,
        description=recipe_data.description,
        categories=assigned_categories,
        ingredients=assigned_ingredients,
        instructions=assigned_instructions,
        tips=assigned_tips
    )

    try:
        db.add(new_recipe)
        await db.commit()
        await db.refresh(new_recipe)
        return new_recipe

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Помилка при збереженні рецепта: {str(e)}"
        )


@router.put("/recipes/{recipe_id}", response_model=schemas.RecipeDetailResponse)
async def update_recipe(
        recipe_id: int,
        recipe_data: schemas.RecipeCreate,
        db: AsyncSession = Depends(get_db),
        _=Depends(verify_api_key)
):
    stmt = (
        select(models.Recipe)
        .where(models.Recipe.id == recipe_id)
        .options(
            selectinload(models.Recipe.categories),
            selectinload(models.Recipe.ingredients),
            selectinload(models.Recipe.instructions),
            selectinload(models.Recipe.tips)
        )
    )
    result = await db.execute(stmt)
    db_recipe = result.unique().scalar_one_or_none()

    if not db_recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Рецепт з ID {recipe_id} не знайдено"
        )

    db_recipe.title = recipe_data.title
    db_recipe.description = recipe_data.description

    try:
        if recipe_data.category_names is not None:
            new_categories = []
            for cat_name in recipe_data.category_names:
                stmt = select(models.Category).where(models.Category.name == cat_name)
                res = await db.execute(stmt)
                category = res.scalar_one_or_none()
                if not category:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Категорію з назвою '{cat_name}' не знайдено"
                    )
                new_categories.append(category)
            db_recipe.categories = new_categories

        if recipe_data.ingredients is not None:
            db_recipe.ingredients.clear()
            for ing in recipe_data.ingredients:
                db_recipe.ingredients.append(
                    models.RecipeIngredient(name=ing.name, amount=ing.amount)
                )

        if recipe_data.instructions is not None:
            db_recipe.instructions.clear()
            for step in recipe_data.instructions:
                db_recipe.instructions.append(
                    models.RecipeInstruction(step=step.step, text=step.text)
                )

        if recipe_data.tips is not None:
            db_recipe.tips.clear()
            for tip in recipe_data.tips:
                db_recipe.tips.append(
                    models.RecipeTip(text=tip.text)
                )

        await db.commit()
        await db.refresh(db_recipe)
        return db_recipe

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Помилка при оновленні рецепта: {str(e)}"
        )


@router.delete("/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe(
        recipe_id: int,
        db: AsyncSession = Depends(get_db),
        _=Depends(verify_api_key)
):
    stmt = select(models.Recipe).where(models.Recipe.id == recipe_id)
    result = await db.execute(stmt)
    recipe = result.unique().scalar_one_or_none()

    if not recipe:
        raise HTTPException(status_code=404, detail="Рецепт не знайдено")

    await db.delete(recipe)
    await db.commit()
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
