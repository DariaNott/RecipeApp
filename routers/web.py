from fastapi import APIRouter, Request, Depends
from templates import templates
from dependencies import get_recipe_service
from services.recipe_service import RecipeService

router = APIRouter(tags=["Web UI"])


@router.get("/")
async def index(
        request: Request,
        page: int = 1,
        category_id: int = None,
        search_query: str = None,
        sort: str = "newest",
        recipe_service: RecipeService = Depends(get_recipe_service)
):
    categories, recipes_page, pagination = await recipe_service.get_index_page_data(
        page=page, category_id=category_id, search_query=search_query, sort=sort
    )

    context = {
        "request": request,
        "recipes": recipes_page,
        "categories": categories,
        "selected_category": category_id,
        "search_query": search_query or "",
        "current_sort": sort,
        "pagination": pagination
    }

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return templates.TemplateResponse(request=request,
                                          name="partials/recipes_list.html",
                                          context=context
                                          )

    return templates.TemplateResponse(request=request,
                                      name="index.html",
                                      context=context
                                      )


@router.get("/recipe/{recipe_id}")
async def recipe_detail(
        request: Request,
        recipe_id: int,
        recipe_service: RecipeService = Depends(get_recipe_service)
):
    recipe, categories, recipe_links_map = await recipe_service.get_recipe_detail_data(recipe_id)

    return templates.TemplateResponse(
        request=request,
        name="recipe.html",
        context={
            "request": request,
            "recipe": recipe,
            "categories": categories,
            "recipe_links_map": recipe_links_map
        }
    )
