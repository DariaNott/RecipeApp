from app import app, db, Recipe, Category, Ingredient, RecipeIngredient, InstructionStep, RecipeTip
from datetime import datetime
import json

with open('recipes.json', 'r', encoding='utf-8') as f:
    DATA = json.load(f)


def seed_recipes():
    with app.app_context():
        for item in DATA:
            # 1. Створюємо рецепт
            recipe = Recipe(
                title=item['title'],
                description=item['description'],
                created_date=datetime.now()
            )

            # 2. Обробка категорій
            for cat_name in item['categories']:
                category = db.session.query(Category).filter_by(title=cat_name).first()
                if not category:
                    category = Category(title=cat_name)
                    db.session.add(category)
                recipe.categories.append(category)

            db.session.add(recipe)
            db.session.flush() # Отримуємо ID рецепта для зв'язків

            # 3. Обробка інгредієнтів
            for ing in item['ingredients']:
                ingredient = db.session.query(Ingredient).filter_by(title=ing['title']).first()
                if not ingredient:
                    ingredient = Ingredient(title=ing['title'], title_genitive=ing['genitive'])
                    db.session.add(ingredient)
                    db.session.flush()

                ri = RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    amount=ing['amount'],
                    measure=ing['measure']
                )
                db.session.add(ri)

            # 4. Обробка інструкцій
            for idx, step_text in enumerate(item['instructions']):
                step = InstructionStep(
                    recipe_id=recipe.id,
                    description=step_text,
                    step_order=idx + 1
                )
                db.session.add(step)

            # 5. Обробка порад
            for tip_text in item['tips']:
                tip = RecipeTip(recipe_id=recipe.id, text=tip_text)
                db.session.add(tip)

        db.session.commit()
        print("Базу успішно заповнено!")

if __name__ == "__main__":
    seed_recipes()