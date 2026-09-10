import pytest
from unittest.mock import AsyncMock
from fastapi import HTTPException, status

import models
import schemas
from services.category_service import CategoryService


@pytest.fixture
def mock_category_repo():
    return AsyncMock()


@pytest.fixture
def category_service(mock_category_repo):
    return CategoryService(category_repo=mock_category_repo)


@pytest.mark.asyncio
async def test_get_all_categories_success(category_service, mock_category_repo):
    fake_categories = [
        models.Category(id=1, name="Десерти", parent_id=None),
        models.Category(id=2, name="Торти", parent_id=1)
    ]
    mock_category_repo.get_all.return_value = fake_categories

    result = await category_service.get_all_categories()

    assert len(result) == 2
    assert result[0].name == "Десерти"
    mock_category_repo.get_all.assert_called_once()


@pytest.mark.asyncio
async def test_create_category_success(category_service, mock_category_repo):
    category_data = schemas.CategoryCreate(name="Супи", parent_id=None)
    created_category = models.Category(id=1, name="Супи", parent_id=None)

    mock_category_repo.get_by_name.return_value = None
    mock_category_repo.create.return_value = created_category

    result = await category_service.create_category(category_data)

    assert result.id == 1
    assert result.name == "Супи"
    mock_category_repo.get_by_name.assert_called_once_with("Супи")
    mock_category_repo.create.assert_called_once_with(category_data)


@pytest.mark.asyncio
async def test_create_category_duplicate_name_raises_400(category_service, mock_category_repo):
    category_data = schemas.CategoryCreate(name="Десерти", parent_id=None)
    mock_category_repo.get_by_name.return_value = models.Category(id=1, name="Десерти")

    with pytest.raises(HTTPException) as exc_info:
        await category_service.create_category(category_data)

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in exc_info.value.detail
    mock_category_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_category_with_valid_parent_success(category_service, mock_category_repo):
    category_data = schemas.CategoryCreate(name="Торти", parent_id=1)
    parent_category = models.Category(id=1, name="Десерти")
    created_category = models.Category(id=2, name="Торти", parent_id=1)

    mock_category_repo.get_by_name.return_value = None
    mock_category_repo.get_by_id.return_value = parent_category
    mock_category_repo.create.return_value = created_category

    result = await category_service.create_category(category_data)

    assert result.parent_id == 1
    mock_category_repo.get_by_id.assert_called_once_with(1)
    mock_category_repo.create.assert_called_once_with(category_data)


@pytest.mark.asyncio
async def test_create_category_parent_not_found_raises_404(category_service, mock_category_repo):
    category_data = schemas.CategoryCreate(name="Торти", parent_id=999)
    mock_category_repo.get_by_name.return_value = None
    mock_category_repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await category_service.create_category(category_data)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail
    mock_category_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_category_repo_error_raises_500(category_service, mock_category_repo):
    category_data = schemas.CategoryCreate(name="Салати", parent_id=None)
    mock_category_repo.get_by_name.return_value = None
    mock_category_repo.create.side_effect = Exception("Database failure")

    with pytest.raises(HTTPException) as exc_info:
        await category_service.create_category(category_data)

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Database failure" in exc_info.value.detail
