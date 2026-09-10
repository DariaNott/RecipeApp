import pytest
from unittest.mock import AsyncMock
from fastapi import HTTPException, status

import models
import schemas
from services.recipe_service import RecipeService


@pytest.fixture
def mock_recipe_repo():
    return AsyncMock()


@pytest.fixture
def mock_category_repo():
    return AsyncMock()


@pytest.fixture
def recipe_service(mock_recipe_repo, mock_category_repo):
    return RecipeService(
        recipe_repo=mock_recipe_repo,
        category_repo=mock_category_repo
    )


@pytest.mark.asyncio
async def test_get_index_page_data_success(recipe_service, mock_recipe_repo, mock_category_repo):
    fake_categories = [models.Category(id=1, name="Десерти")]
    fake_recipes = [models.Recipe(id=1, title="Борщ")]
    fake_pagination = {"page": 1, "total_pages": 1}

    mock_category_repo.get_all_with_children.return_value = fake_categories
    mock_recipe_repo.get_paginated_list.return_value = (fake_recipes, fake_pagination)

    categories, recipes, pagination = await recipe_service.get_index_page_data(
        page=1, category_id=None, search_query="", sort="newest"
    )

    assert categories == fake_categories
    assert recipes == fake_recipes
    assert pagination == fake_pagination
    mock_category_repo.get_all_with_children.assert_called_once()
    mock_recipe_repo.get_paginated_list.assert_called_once_with(
        page=1, category_id=None, search_query="", sort="newest"
    )


@pytest.mark.asyncio
async def test_get_recipe_detail_data_not_found_raises_404(recipe_service, mock_recipe_repo):
    mock_recipe_repo.get_by_id_with_details.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await recipe_service.get_recipe_detail_data(recipe_id=999)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "Recipe not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_recipe_success(recipe_service, mock_recipe_repo, mock_category_repo):
    recipe_data = schemas.RecipeCreate(
        title="Паста",
        description="Смачна паста",
        category_names=["Італійська"],
        ingredients=[schemas.RecipeIngredientBase(name="Спагеті", amount="200g")],
        instructions=[schemas.RecipeInstructionBase(step=1, text="Зварити")],
        tips=[schemas.RecipeTipBase(text="Посипати сиром")]
    )
    fake_category = models.Category(id=1, name="Італійська")
    mock_category_repo.get_by_name.return_value = fake_category

    fake_created_recipe = models.Recipe(id=10, title="Паста")
    mock_recipe_repo.create.return_value = fake_created_recipe

    result = await recipe_service.create_recipe(recipe_data)

    assert result.id == 10
    mock_category_repo.get_by_name.assert_called_once_with("Італійська")
    mock_recipe_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_recipe_category_not_found_raises_404(recipe_service, mock_category_repo, mock_recipe_repo):
    recipe_data = schemas.RecipeCreate(
        title="Піца",
        description="Опис",
        category_names=["Невідома Категорія"],
        ingredients=[],
        instructions=[],
        tips=[]
    )
    mock_category_repo.get_by_name.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await recipe_service.create_recipe(recipe_data)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail
    mock_recipe_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_update_recipe_success(recipe_service, mock_recipe_repo, mock_category_repo):
    existing_recipe = models.Recipe(
        id=1,
        title="Стара назва",
        description="Старий опис",
        categories=[],
        ingredients=[],
        instructions=[],
        tips=[]
    )
    mock_recipe_repo.get_by_id_with_details.return_value = existing_recipe

    update_data = schemas.RecipeCreate(
        title="Нова назва",
        description="Новий опис",
        category_names=[],
        ingredients=[],
        instructions=[],
        tips=[]
    )

    result = await recipe_service.update_recipe(recipe_id=1, recipe_data=update_data)

    assert result.title == "Нова назва"
    assert result.description == "Новий опис"
    mock_recipe_repo.commit_and_refresh.assert_called_once_with(existing_recipe)


@pytest.mark.asyncio
async def test_update_recipe_not_found_raises_404(recipe_service, mock_recipe_repo):
    mock_recipe_repo.get_by_id_with_details.return_value = None
    update_data = schemas.RecipeCreate(
        title="Нова назва",
        description="Опис",
        category_names=[],
        ingredients=[],
        instructions=[],
        tips=[]
    )

    with pytest.raises(HTTPException) as exc_info:
        await recipe_service.update_recipe(recipe_id=999, recipe_data=update_data)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_recipe_success(recipe_service, mock_recipe_repo):
    mock_recipe_repo.get_by_id.return_value = models.Recipe(id=1, title="Суп")

    await recipe_service.delete_recipe(recipe_id=1)

    mock_recipe_repo.delete_by_id.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_recipe_not_found_raises_404(recipe_service, mock_recipe_repo):
    mock_recipe_repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await recipe_service.delete_recipe(recipe_id=999)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    mock_recipe_repo.delete_by_id.assert_not_called()
