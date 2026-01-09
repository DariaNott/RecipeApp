import json
import os
from datetime import datetime
from app import app, db, Recipe, Category, Ingredient, RecipeIngredient, InstructionStep, RecipeTip
from sqlalchemy import select


def import_everything():
    with app.app_context():
        # --- 1. КАТЕГОРІЇ (з урахуванням ієрархії) ---
        if os.path.exists('categories.json'):
            with open('categories.json', 'r', encoding='utf-8') as f:
                cats_data = json.load(f)

            # Спершу створюємо всі, щоб уникнути помилок parent_id
            for c in cats_data:
                if not db.session.execute(select(Category).where(Category.title == c['title'])).scalar_one_or_none():
                    db.session.add(Category(title=c['title']))
            db.session.commit()

            # Проставляємо батьківські категорії
            for c in cats_data:
                if c.get('parent_title'):
                    child = db.session.execute(select(Category).where(Category.title == c['title'])).scalar_one()
                    parent = db.session.execute(
                        select(Category).where(Category.title == c['parent_title'])).scalar_one()
                    child.parent_id = parent.id
            db.session.commit()
            print("✅ Категорії імпортовано.")

        # --- 2. ІНГРЕДІЄНТИ ---
        if os.path.exists('ingredients.json'):
            with open('ingredients.json', 'r', encoding='utf-8') as f:
                ings_data = json.load(f)
            for i in ings_data:
                if not db.session.execute(
                        select(Ingredient).where(Ingredient.title == i['title'])).scalar_one_or_none():
                    db.session.add(Ingredient(
                        title=i['title'],
                        title_genitive=i.get('genitive', i['title'])
                    ))
            db.session.commit()
            print("✅ Інгредієнти імпортовано.")

        # --- 3. РЕЦЕПТИ ---
        if os.path.exists('recipes.json'):
            with open('recipes.json', 'r', encoding='utf-8') as f:
                recipes_data = json.load(f)

            for r_data in recipes_data:
                # Перевірка на дублікат рецепта
                if db.session.execute(select(Recipe).where(Recipe.title == r_data['title'])).scalar_one_or_none():
                    continue

                recipe = Recipe(
                    title=r_data['title'],
                    description=r_data.get('description', ''),
                    created_date=datetime.now()
                )

                # Додаємо категорії
                for cat_name in r_data.get('category_names', []):
                    cat = db.session.execute(select(Category).where(Category.title == cat_name)).scalar_one_or_none()
                    if cat: recipe.categories.append(cat)

                db.session.add(recipe)
                db.session.flush()

                # Додаємо інгредієнти
                for ing_item in r_data.get('ingredients', []):
                    ing_obj = db.session.execute(
                        select(Ingredient).where(Ingredient.title == ing_item['name'])).scalar_one_or_none()
                    if ing_obj:
                        ri = RecipeIngredient(
                            recipe_id=recipe.id,
                            ingredient_id=ing_obj.id,
                            amount=ing_item.get('amount'),
                            measure=ing_item.get('measure')
                        )
                        db.session.add(ri)

                # Додаємо інструкції (тепер це список словників)
                for idx, step_data in enumerate(r_data.get('instructions', [])):
                    # Підтримка як просто тексту, так і словника
                    desc = step_data['text'] if isinstance(step_data, dict) else step_data
                    order = step_data.get('step', idx + 1) if isinstance(step_data, dict) else idx + 1

                    db.session.add(InstructionStep(
                        recipe_id=recipe.id,
                        description=desc,
                        step_order=order
                    ))

                # Додаємо поради
                for tip_text in r_data.get('tips', []):
                    db.session.add(RecipeTip(recipe_id=recipe.id, text=tip_text))

            db.session.commit()
            print(f"✅ Рецепти імпортовано.")


if __name__ == "__main__":
    import_everything()