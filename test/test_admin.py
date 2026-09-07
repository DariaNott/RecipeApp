import pytest
import models
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

HEADERS = {"X-API-KEY": "recipe3inN8shEYHHSGNlivZr1nJX3Da9ZTRqi"}


async def test_create_recipe_without_api_key(client: AsyncClient):
    response = await client.post("/api/v1/admin/recipes/", json={"title": "Тест"})
    assert response.status_code == 403


async def test_create_category_success(client: AsyncClient):
    payload = {
        "name": "Закуски",
        "parent_id": None
    }
    response = await client.post("/api/v1/admin/categories/", json=payload, headers=HEADERS)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Закуски"
    assert "id" in data


async def test_create_recipe_category_not_found(client: AsyncClient):
    recipe_payload = {
        "title": "Хлібці",
        "description": "Смачні хлібці",
        "category_names": ["Неіснуюча Категорія"],
        "ingredients": [],
        "instructions": [],
        "tips": []
    }
    response = await client.post("/api/v1/admin/recipes/", json=recipe_payload, headers=HEADERS)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


async def test_create_recipe_success(client: AsyncClient, db_session: AsyncSession):
    category = models.Category(name="Італійська кухня")
    db_session.add(category)
    await db_session.commit()

    recipe_payload = {
        "title": "Грісіні",
        "description": "Традиційні італійські хлібні палички.",
        "category_names": ["Італійська кухня"],
        "ingredients": [
            {"name": "Борошно", "amount": "250 г"}
        ],
        "instructions": [
            {"step": 1, "text": "Замісити тісто."}
        ],
        "tips": []
    }

    response = await client.post("/api/v1/admin/recipes/", json=recipe_payload, headers=HEADERS)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Грісіні"
    assert len(data["categories"]) == 1
    assert data["categories"][0]["name"] == "Італійська кухня"
    assert len(data["ingredients"]) == 1
    assert data["ingredients"][0]["name"] == "Boroshno" or data["ingredients"][0]["name"] == "Борошно"