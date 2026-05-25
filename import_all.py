import json
import asyncio
from sqlalchemy import select, text
from database import AsyncSessionLocal, engine, Base
import models

# Назва проміжної таблиці Many-to-Many згідно з вашою структурою
ASSOCIATION_TABLE_NAME = "recipe_categories"


async def load_json_data(file_path: str):
    """Читання файлу JSON з підтримкою UTF-8"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


async def import_data():
    print("⏳ Початок повного імпорту та адаптації даних під вашу структуру JSON...")

    # КРОК 0: Автоматично створюємо всі таблиці в базі даних, якщо їх немає
    async with engine.begin() as conn:
        print("🛠️ Перевірка та створення таблиць у базі даних...")
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:

        # ==========================================
        # 1. ІМПОРТ КАТЕГОРІЙ
        # ==========================================
        categories_data = await load_json_data("resources\\categories.json")
        print(f"📦 Завантажено {len(categories_data)} категорій з JSON. Обробка ієрархії...")

        # Словник для швидкого пошуку ID категорії за її текстовою назвою (title -> id)
        category_name_to_id = {}

        # Крок 1.1: Створюємо категорії в базі, генеруючи їм ID автоматично
        for idx, cat_dict in enumerate(categories_data, start=1):
            title = cat_dict["title"].strip()
            category = models.Category(
                id=idx,
                name=title,
                parent_id=None
            )
            session.add(category)
            category_name_to_id[title] = idx

        await session.flush()  # Фіксуємо у сесії, щоб категорії отримали свої ID

        # Крок 1.2: Будуємо зв'язки parent_id на основі parent_title з вашого JSON
        for cat_dict in categories_data:
            title = cat_dict["title"].strip()
            parent_title = cat_dict.get("parent_title")

            if parent_title:
                parent_title = parent_title.strip()
                current_id = category_name_to_id.get(title)
                parent_id = category_name_to_id.get(parent_title)

                if current_id and parent_id:
                    stmt = text("UPDATE categories SET parent_id = :p_id WHERE id = :c_id")
                    await session.execute(stmt, {"p_id": parent_id, "c_id": current_id})

        await session.flush()
        print("✅ Категорії та їх ієрархія успішно імпортовані!")

        # ==========================================
        # 2. ІМПОРТ РЕЦЕПТІВ ТА ПОВ'ЯЗАНИХ ДАНИХ
        # ==========================================
        recipes_data = await load_json_data("resources\\recipes.json")
        print(f"📦 Завантажено {len(recipes_data)} рецептів з JSON. Обробка відносин...")

        # Генеруємо унікальний ID для кожного рецепта через лічильник
        for idx, rec_dict in enumerate(recipes_data, start=1):
            recipe_id = rec_dict.get("id", idx)

            # Створюємо базовий об'єкт Рецепту (БЕЗ cooking_time)
            recipe = models.Recipe(
                id=recipe_id,
                title=rec_dict["title"],
                description=rec_dict.get("description", "")
            )
            session.add(recipe)
            await session.flush()

            # Додаємо зв'язки Many-to-Many з категоріями через текстовий масив category_names
            if "category_names" in rec_dict and rec_dict["category_names"]:
                for cat_name in rec_dict["category_names"]:
                    cat_name = cat_name.strip()
                    cat_id = category_name_to_id.get(cat_name)

                    if cat_id:
                        stmt = text(
                            f"INSERT OR IGNORE INTO {ASSOCIATION_TABLE_NAME} (recipe_id, category_id) "
                            f"VALUES (:r_id, :c_id)"
                        )
                        await session.execute(stmt, {"r_id": recipe.id, "c_id": cat_id})
                    else:
                        print(
                            f"⚠️ Попередження: категорію '{cat_name}' для рецепту '{recipe.title}' не знайдено в базі!")

            # Додаємо інгредієнти рецепта (One-to-Many) з перевіркою на None
            if "ingredients" in rec_dict:
                for ing_info in rec_dict["ingredients"]:
                    raw_amount = ing_info.get("amount")

                    # Захист від текстових "None", пустих рядків чи null в JSON
                    if raw_amount is None or str(raw_amount).strip() == "" or str(raw_amount) == "None":
                        final_amount = None
                    else:
                        final_amount = str(raw_amount).strip()

                    recipe_ingredient = models.RecipeIngredient(
                        recipe_id=recipe.id,
                        name=ing_info["name"].strip(),
                        amount=final_amount
                    )
                    session.add(recipe_ingredient)

            # Додаємо інструкції кроками (One-to-Many)
            if "instructions" in rec_dict:
                for ins in rec_dict["instructions"]:
                    recipe_instruction = models.RecipeInstruction(
                        recipe_id=recipe.id,
                        step=ins["step"],
                        text=ins["text"]
                    )
                    session.add(recipe_instruction)

            # Додаємо поради (tips), якщо вони є
            if "tips" in rec_dict:
                for tip_text in rec_dict["tips"]:
                    recipe_tip = models.RecipeTip(
                        recipe_id=recipe.id,
                        text=tip_text
                    )
                    session.add(recipe_tip)

        # Робимо фінальний загальний комміт для збереження всіх даних в один момент
        await session.commit()
        print("🎉 ФІНАЛЬНИЙ ІМПОРТ ЗАВЕРШЕНО! Усі дані успішно імпортовано!")


if __name__ == "__main__":
    asyncio.run(import_data())