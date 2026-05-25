from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from typing import List

import models
import schemas
from dependencies import get_db

router = APIRouter(prefix="/api/v1/admin", tags=["Admin CRUD API"])

# Налаштування безпеки через заголовок X-API-KEY
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

# 🤫 Ваш секретний ключ (бажано тримати в .env)
SECRET_API_KEY = "my_super_secret_recipe_app_key_123"


async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != SECRET_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Невірний або відсутній API Ключ"
        )
    return api_key


# ==========================================
# 1. READ (GET) — Список усіх рецептів для адміна
# ==========================================
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


# ==========================================
# 2. CREATE (POST) — Створення рецепта
# ==========================================
@router.post("/recipes/", response_model=schemas.RecipeDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe(
        recipe_data: schemas.RecipeCreate,
        db: AsyncSession = Depends(get_db),
        _=Depends(verify_api_key)
):
    # Створюємо основне тіло рецепта
    new_recipe = models.Recipe(
        title=recipe_data.title,
        description=recipe_data.description
    )
    db.add(new_recipe)
    await db.flush()  # генеруємо id рецепта

    # Прив'язуємо категорії Many-to-Many
    if recipe_data.category_names:
        cat_stmt = select(models.Category).where(
            func.py_lower(models.Category.name).in_([name.lower() for name in recipe_data.category_names])
        )
        cat_result = await db.execute(cat_stmt)
        for category in cat_result.scalars().all():
            new_recipe.categories.append(category)

    # Додаємо інгредієнти
    for ing in recipe_data.ingredients:
        db.add(models.RecipeIngredient(recipe_id=new_recipe.id, name=ing.name, amount=ing.amount))

    # Додаємо інструкції
    for idx, inst in enumerate(recipe_data.instructions, start=1):
        db.add(models.RecipeInstruction(recipe_id=new_recipe.id, step=inst.step or idx, text=inst.text))

    await db.commit()

    # Повертаємо об'єкт із підвантаженими зв'язками
    res = await db.execute(
        select(models.Recipe)
        .where(models.Recipe.id == new_recipe.id)
        .options(
            selectinload(models.Recipe.categories),
            selectinload(models.Recipe.ingredients),
            selectinload(models.Recipe.instructions),
            selectinload(models.Recipe.tips)
        )
    )
    return res.unique().scalar_one()


# ==========================================
# 3. UPDATE (PUT) — Повне оновлення рецепта
# ==========================================
@router.put("/recipes/{recipe_id}", response_model=schemas.RecipeDetailResponse)
async def update_recipe(
        recipe_id: int,
        recipe_data: schemas.RecipeCreate,
        db: AsyncSession = Depends(get_db),
        _=Depends(verify_api_key)
):
    # Перевіряємо, чи є такий рецепт
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
        raise HTTPException(status_code=404, detail="Рецепт не знайдено")

    # Оновлюємо базові поля
    recipe.title = recipe_data.title
    recipe.description = recipe_data.description

    # Оновлюємо Many-to-Many категорії (очищуємо старі, додаємо нові)
    recipe.categories.clear()
    if recipe_data.category_names:
        cat_stmt = select(models.Category).where(
            func.py_lower(models.Category.name).in_([name.lower() for name in recipe_data.category_names])
        )
        cat_result = await db.execute(cat_stmt)
        for category in cat_result.scalars().all():
            recipe.categories.append(category)

    # Видаляємо старі інгредієнти та кроки (завдяки cascade орм за цим стежить, але надійніше через delete)
    await db.execute(delete(models.RecipeIngredient).where(models.RecipeIngredient.recipe_id == recipe_id))
    await db.execute(delete(models.RecipeInstruction).where(models.RecipeInstruction.recipe_id == recipe_id))

    # Записуємо нові інгредієнти
    for ing in recipe_data.ingredients:
        db.add(models.RecipeIngredient(recipe_id=recipe.id, name=ing.name, amount=ing.amount))

    # Записуємо нові інструкції
    for idx, inst in enumerate(recipe_data.instructions, start=1):
        db.add(models.RecipeInstruction(recipe_id=recipe.id, step=inst.step or idx, text=inst.text))

    await db.commit()

    # Повертаємо свіжий стан з бази
    refreshed_result = await db.execute(stmt)
    return refreshed_result.unique().scalar_one()


# ==========================================
# 4. DELETE — Видалення рецепта
# ==========================================
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