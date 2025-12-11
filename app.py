from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import select, desc
from models import db, seed_data, Recipe, Category, Ingredient, RecipeIngredient, InstructionStep
from forms import RecipeForm
from datetime import datetime
import mimetypes
import re

# TODO: перейти на веб-сервер Nginx + Gunicorn перед викатом в прод
app = Flask(__name__)
mimetypes.add_type('image/svg+xml', '.svg')

# --- DB initialisation  ---
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recipes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    seed_data(app)


# ----------------------------------------------------
# Custom filters Jinja2
# ----------------------------------------------------

def format_datetime(value, format="%d.%m.%Y"):
    if value is None:
        return ""
    return value.strftime(format)


def format_amount(value):
    """
    Форматує числову кількість:
    1. Перетворює поширені дроби (0.5, 0.25) на символи Unicode (½, ¼).
    2. Якщо це ціле число (наприклад, 3.0), виводить його як int (3).
    3. В іншому випадку виводить число з плаваючою комою (наприклад, 1.33).
    """
    if value is None:
        return ""

    fraction_map = {
        0.25: '¼',
        0.5: '½',
        0.75: '¾',
        1 / 3: '⅓',
        2 / 3: '⅔',
    }

    rounded_value = round(value, 3)
    if rounded_value in fraction_map:
        return fraction_map[rounded_value]

    if value > 1 and value % 1 != 0:
        integer_part = int(value)
        fractional_part = value - integer_part

        rounded_fraction = round(fractional_part, 3)
        if rounded_fraction in fraction_map:
            return f"{integer_part} {fraction_map[rounded_fraction]}"

        return f"{value:.2f}"

    if value == int(value):
        return int(value)

    return f"{value:.2f}"

@app.template_filter('trim_zeros')
def trim_zeros_filter(value):
    """Видаляє зайві нулі з кінця числа (наприклад, 3.00 -> 3)"""
    if value is None:
        return ""
    return ('%.2f' % float(value)).rstrip('0').rstrip('.')


## Register filters
app.jinja_env.filters['datetime'] = format_datetime
app.jinja_env.filters['amount'] = format_amount  # РЕЄСТРУЄМО НОВИЙ ФІЛЬТР


# ----------------------------------------------------
# Routes
# ----------------------------------------------------

@app.context_processor
def inject_global_data():
    """Передає список головних категорій у кожен шаблон."""

    # Вибираємо лише головні категорії (ті, що не мають parent_id)
    main_categories = db.session.execute(
        select(Category).where(Category.parent_id == None).order_by(Category.title)
    ).scalars().all()

    return dict(main_categories=main_categories)


@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    base_query = select(Recipe).order_by(desc(Recipe.created_date))
    recipes_paginated = db.paginate(
        base_query,
        page=page,
        per_page=15,
        error_out=False
    )

    return render_template(
        'index.html',
        all_recipes=recipes_paginated.items,
        pagination=recipes_paginated
    )


@app.route('/recipe/<int:recipe_id>')
def recipe(recipe_id):
    required_recipe = db.get_or_404(Recipe, recipe_id)
    return render_template('recipe.html', recipe=required_recipe)


# helper for add_recipe()
def convert_amount(amount_str):
    if not amount_str:
        return None
    amount_str = amount_str.strip()
    try:
        return float(amount_str)
    except ValueError:
        match = re.match(r'(\d+)?\s*(\d+)/(\d+)', amount_str)
        if match:
            whole = int(match.group(1) or 0)
            numerator = int(match.group(2))
            denominator = int(match.group(3))
            if denominator != 0:
                return float(whole) + (float(numerator) / denominator)
    return None


@app.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    all_categories = db.session.execute(select(Category).order_by(Category.title)).scalars().all()

    ingredient_data_for_js = db.session.execute(
        select(Ingredient.title, Ingredient.title_genitive)
        .order_by(Ingredient.title)
    ).all()

    ingredient_titles = [
        {'title': ing.title, 'title_genitive': ing.title_genitive or ing.title}
        for ing in ingredient_data_for_js
    ]


    if request.method == 'POST':
        try:
            title = request.form['title'].strip()
            description = request.form.get('description', '').strip()
            category_ids = request.form.getlist('categories')

            if not title or not category_ids:
                flash('Потрібно вказати назву та обрати принаймні одну категорію.', 'warning')
                return redirect(url_for('add_recipe'))

            new_recipe = Recipe(
                title=title,
                description=description,
                created_date=datetime.now()
            )

            selected_categories = db.session.execute(
                select(Category).where(Category.id.in_(category_ids))
            ).scalars().all()

            for cat in selected_categories:
                new_recipe.categories.append(cat)

            db.session.add(new_recipe)
            db.session.flush()

            amounts = request.form.getlist('amount')
            measures = request.form.getlist('measure')
            ingredient_titles_input = request.form.getlist('ingredient_title')
            ingredient_titles_genitive = request.form.getlist('ingredient_title_genitive')  # <--- НОВЕ ПОЛЕ

            for i in range(len(ingredient_titles_input)):
                title_input = ingredient_titles_input[i].strip()

                if not title_input:
                    continue

                amount_str = amounts[i].strip() if i < len(amounts) and amounts[i] else None
                measure = measures[i].strip() if i < len(measures) and measures[i] else None
                title_genitive_input = ingredient_titles_genitive[i].strip() if i < len(ingredient_titles_genitive) and \
                                                                                ingredient_titles_genitive[i] else None

                existing_ingredient = db.session.execute(
                    select(Ingredient).where(Ingredient.title == title_input)
                ).scalar_one_or_none()

                if existing_ingredient is None:
                    existing_ingredient = Ingredient(
                        title=title_input,
                        title_genitive=title_genitive_input or title_input  # Зберігаємо Р.в.
                    )
                    db.session.add(existing_ingredient)
                    db.session.flush()

                    #TODO: Якщо інгредієнт вже існує, але користувач ввів Р.в. для нього, ми поки що його не оновлюємо. можна додати пізніше

                recipe_ingredient = RecipeIngredient(
                    recipe_id=new_recipe.id,
                    ingredient_id=existing_ingredient.id,
                    amount=convert_amount(amount_str),
                    measure=measure
                )
                db.session.add(recipe_ingredient)

            instruction_descriptions = request.form.getlist('instruction_description')
            step_orders = request.form.getlist('step_order')

            for i in range(len(instruction_descriptions)):
                description = instruction_descriptions[i].strip()

                if description:
                    step = InstructionStep(
                        recipe_id=new_recipe.id,
                        description=description,
                        step_order=int(step_orders[i]) if i < len(step_orders) else (i + 1)
                    )
                    db.session.add(step)

            db.session.commit()

            flash('Рецепт успішно додано!', 'success')
            return redirect(url_for('recipe', recipe_id=new_recipe.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Помилка при додаванні рецепту. Спробуйте ще раз. Деталі: {e}', 'danger')
            return redirect(url_for('add_recipe'))

    return render_template(
        'add_recipe.html',
        categories=all_categories,
        ingredient_titles_json=ingredient_titles
    )

if __name__ == '__main__':
    app.run(debug=True)
