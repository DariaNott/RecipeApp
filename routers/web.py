import re
import math
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from dependencies import get_db

router = APIRouter(tags=["Web UI"])

templates = Jinja2Templates(directory="templates")


# --- custom JINJA2 filters ---
def filter_datetime(value):
    if value is None:
        return "Не вказано"
    try:
        return value.strftime("%d.%m.%Y %H:%M")
    except AttributeError:
        return str(value)


def filter_link_recipes(value):
    """Search [[Recipe Title]] and convert to HTML link"""
    if value is None:
        return ""

    def replace_link(match):
        recipe_title = match.group(1)
        clean_title = recipe_title.lower().strip()

        recipe_id = RECIPE_LINKS_MAP.get(clean_title)
        if recipe_id:
            return f'<a href="/recipe/{recipe_id}" class="recipe-wiki-link">{recipe_title}</a>'

        return recipe_title

    return re.sub(r'\[\[(.*?)\]\]', replace_link, str(value))


RECIPE_LINKS_MAP = {}


async def refresh_recipe_links_map(db: AsyncSession):
    global RECIPE_LINKS_MAP
    try:
        result = await db.execute(select(models.Recipe.id, models.Recipe.title))
        recipes_list = result.all()
        RECIPE_LINKS_MAP = {row.title.lower().strip(): row.id for row in recipes_list}
    except Exception as e:
        print(f"⚠️ Не вдалося оновити карту посилань рецептів: {e}")


templates.env.filters["datetime"] = filter_datetime
templates.env.filters["link_recipes"] = filter_link_recipes


@router.get("/")
async def index(
        request: Request,
        page: int = 1,
        category_id: int = None,
        search_query: str = None,
        sort: str = "newest",
        db: AsyncSession = Depends(get_db)
):
    await refresh_recipe_links_map(db)

    cat_result = await db.execute(
        select(models.Category)
        .options(selectinload(models.Category.children))
    )
    categories = cat_result.unique().scalars().all()

    stmt = select(models.Recipe)

    if search_query and search_query.strip():
        q = f"%{search_query.strip()}%"
        stmt = stmt.where(
            models.Recipe.title.ilike(q) | models.Recipe.description.ilike(q)
        )

    if category_id:
        sub_cats_res = await db.execute(
            select(models.Category.id).where(models.Category.parent_id == category_id)
        )
        sub_cat_ids = sub_cats_res.scalars().all()

        target_category_ids = [category_id] + list(sub_cat_ids)

        stmt = stmt.where(
            models.Recipe.categories.any(models.Category.id.in_(target_category_ids))
        )

    if sort == "name_asc":
        stmt = stmt.order_by(asc(models.Recipe.title))
    elif sort == "name_desc":
        stmt = stmt.order_by(desc(models.Recipe.title))
    elif sort == "oldest":
        stmt = stmt.order_by(asc(models.Recipe.id))
    else:  # newest
        stmt = stmt.order_by(desc(models.Recipe.id))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total_recipes = count_result.scalar() or 0

    limit = 6
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    recipes_result = await db.execute(stmt)
    recipes_page = recipes_result.scalars().all()

    total_pages = math.ceil(total_recipes / limit) or 1

    pagination = {
        "total": total_recipes,
        "page": page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return templates.TemplateResponse(
            request=request,
            name="partials/recipes_list.html",
            context={
                "request": request,
                "recipes": recipes_page,
                "pagination": pagination,
                "current_sort": sort,
                "search_query": search_query if search_query else "",
                "selected_category": category_id
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "recipes": recipes_page,
            "categories": categories,
            "selected_category": category_id,
            "search_query": search_query,
            "current_sort": sort,
            "pagination": pagination
        }
    )


@router.get("/recipe/{recipe_id}")
async def recipe_detail(request: Request, recipe_id: int, db: AsyncSession = Depends(get_db)):
    await refresh_recipe_links_map(db)

    cat_result = await db.execute(
        select(models.Category)
        .options(selectinload(models.Category.children))
    )
    categories = cat_result.unique().scalars().all()

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

    return templates.TemplateResponse(
        request=request,
        name="recipe.html",
        context={
            "request": request,
            "recipe": recipe,
            "categories": categories,
            "recipe_links_map": RECIPE_LINKS_MAP
        }
    )
