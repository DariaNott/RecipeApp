import json
import os
from datetime import datetime
from app import app, db, Recipe, Category, Ingredient, RecipeIngredient, InstructionStep, RecipeTip
from sqlalchemy import select

from models import User


def import_everything():
    with app.app_context():
        print("🚀 Початок імпорту даних...")

        # --- 1. КАТЕГОРІЇ (з урахуванням ієрархії) ---
        if os.path.exists('resources/categories.json'):
            with open('resources/categories.json', 'r', encoding='utf-8') as f:
                cats_data = json.load(f)

            # Спершу створюємо всі назви, щоб уникнути помилок parent_id
            for c in cats_data:
                existing_cat = db.session.execute(
                    select(Category).where(Category.title == c['title'])).scalar_one_or_none()
                if not existing_cat:
                    db.session.add(Category(title=c['title']))
            db.session.commit()

            # Проставляємо parent_id (батьківські зв'язки)
            for c in cats_data:
                if c.get('parent_title'):
                    child = db.session.execute(select(Category).where(Category.title == c['title'])).scalar_one()
                    parent = db.session.execute(
                        select(Category).where(Category.title == c['parent_title'])).scalar_one()
                    child.parent_id = parent.id
            db.session.commit()
            print("✅ Категорії та їх ієрархія імпортовані.")

        # --- 2. ІНГРЕДІЄНТИ (збереження ваших ID) ---
        if os.path.exists('resources/ingredients.json'):
            with open('resources/ingredients.json', 'r', encoding='utf-8') as f:
                ings_data = json.load(f)
            for i in ings_data:
                # Перевіряємо за ID, щоб не дублювати
                existing_ing = db.session.get(Ingredient, i['id'])
                if not existing_ing:
                    db.session.add(Ingredient(
                        id=i['id'],
                        title=i['title'],
                        title_genitive=i.get('genitive', i['title'])
                    ))
            db.session.commit()
            print("✅ Словник інгредієнтів імпортовано.")

        # --- 3. РЕЦЕПТИ ---
        if os.path.exists('resources/recipes.json'):
            with open('resources/recipes.json', 'r', encoding='utf-8') as f:
                recipes_data = json.load(f)

            for r_data in recipes_data:
                # Перевірка на дублікат за назвою
                existing_recipe = db.session.execute(
                    select(Recipe).where(Recipe.title == r_data['title'])).scalar_one_or_none()
                if existing_recipe:
                    print(f"⚠️ Рецепт '{r_data['title']}' вже існує, пропуск...")
                    continue

                recipe = Recipe(
                    title=r_data['title'],
                    description=r_data.get('description', ''),
                    created_date=datetime.now()
                )

                # Прив'язка категорій
                for cat_name in r_data.get('category_names', []):
                    cat = db.session.execute(select(Category).where(Category.title == cat_name)).scalar_one_or_none()
                    if cat:
                        recipe.categories.append(cat)

                db.session.add(recipe)
                db.session.flush()  # Отримуємо ID нового рецепта

                # Прив'язка інгредієнтів (через ID з вашого JSON)
                for ing_item in r_data.get('ingredients', []):
                    ing_obj = db.session.get(Ingredient, ing_item['id'])
                    if ing_obj:
                        ri = RecipeIngredient(
                            recipe_id=recipe.id,
                            ingredient_id=ing_obj.id,
                            amount=ing_item.get('amount'),
                            measure=ing_item.get('measure')
                        )
                        db.session.add(ri)

                # Додавання інструкцій (кроків)
                for step_data in r_data.get('instructions', []):
                    db.session.add(InstructionStep(
                        recipe_id=recipe.id,
                        description=step_data['text'],
                        step_order=step_data['step']
                    ))

                # Додавання порад (якщо є)
                if 'tips' in r_data:
                    for tip_text in r_data['tips']:
                        db.session.add(RecipeTip(recipe_id=recipe.id, text=tip_text))

            db.session.commit()
            print(f"✅ Рецепти імпортовано успішно!")


def create_admin(password):
    with app.app_context():
        admin = User(username='chef')
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print("✅ Адміна створено!")

if __name__ == "__main__":
    import_everything()
