from itertools import product

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import or_, desc, select
from models import db, Recipe, Category, Ingredient, RecipeIngredient, InstructionStep, RecipeTip, User
from forms import RecipeForm
from datetime import datetime
import mimetypes
import re
import os

# TODO: перейти на веб-сервер Nginx + Gunicorn перед викатом в прод
app = Flask(__name__)
mimetypes.add_type('image/svg+xml', '.svg')

# --- DB initialisation  ---
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URI', 'sqlite:///recipes.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.environ.get('SQL_TRACK_MODS', False)

db.init_app(app)

with app.app_context():
    db.create_all()


# ----------------------------------------------------
# Custom filters Jinja2
# ----------------------------------------------------

@app.template_filter('datetime')
def format_datetime(value, format="%d.%m.%Y"):
    if value is None:
        return ""
    return value.strftime(format)


@app.template_filter('trim_zeros')
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


@app.template_filter('link_recipes')
def link_recipes(text):
    if not text: return ""
    # Шукаємо текст у подвійних дужках [[Назва]]
    pattern = r'\[\[(.*?)\]\]'

    def replace_with_link(match):
        recipe_title = match.group(1)
        # Шукаємо рецепт у базі за назвою
        target_recipe = db.session.execute(select(Recipe).where(Recipe.title == recipe_title)).scalar_one_or_none()
        if target_recipe:
            url = url_for('recipe', recipe_id=target_recipe.id)
            return f'<a href="{url}">{recipe_title}</a>'
        return recipe_title

    linked_text = re.sub(pattern, replace_with_link, text)
    return linked_text


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
    # 1. Отримуємо параметри
    page = request.args.get('page', 1, type=int)
    sort_option = request.args.get('sort', 'newest')  # Перевірте, що тут 'sort'
    query = request.args.get('query', '')
    cat_id = request.args.get('category_id', type=int)

    # 2. Будуємо запит
    stmt = select(Recipe)

    # 3. Сортування (Цей блок має бути ДО пагінації)
    if sort_option == 'name_asc':
        stmt = stmt.order_by(Recipe.title.asc())
    elif sort_option == 'name_desc':
        stmt = stmt.order_by(Recipe.title.desc())
    elif sort_option == 'oldest':
        stmt = stmt.order_by(Recipe.created_date.asc())
    else:
        stmt = stmt.order_by(Recipe.created_date.desc())

    # 4. Фільтрація
    if query:
        stmt = stmt.where(Recipe.title.ilike(f"%{query}%"))
    if cat_id:
        stmt = stmt.where(Recipe.categories.any(Category.id == cat_id))

    # 5. Пагінація
    pagination = db.paginate(stmt, page=page, per_page=9)

    return render_template('index.html',
                           all_recipes=pagination.items,
                           pagination=pagination,
                           current_sort=sort_option,  # Обов'язково передаємо назад!
                           selected_category=cat_id,
                           search_query=query)


@app.route('/recipe/<int:recipe_id>')
def recipe(recipe_id):
    required_recipe = db.get_or_404(Recipe, recipe_id)
    return render_template('recipe.html', recipe=required_recipe)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Куди перенаправляти, якщо не залогінений


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = db.session.execute(select(User).where(User.username == username)).scalar_one_or_none()

        if user and user.check_password(password):
            login_user(user)
            flash('Ви успішно увійшли!', 'success')
            return redirect(url_for('index'))

        flash('Невірний логін або пароль', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


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
@login_required
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

                    # TODO: Якщо інгредієнт вже існує, але користувач ввів Р.в. для нього, ми поки що його не оновлюємо. можна додати пізніше

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

            tip_descriptions = request.form.getlist('tip_description')
            for tip_text in tip_descriptions:
                text = tip_text.strip()
                if text:
                    new_tip = RecipeTip(
                        recipe_id=new_recipe.id,
                        text=text
                    )
                    db.session.add(new_tip)

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


@app.route('/recipe/<int:recipe_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_recipe(recipe_id):
    recipe = db.get_or_404(Recipe, recipe_id)

    all_categories = db.session.execute(select(Category).order_by(Category.title)).scalars().all()
    ingredient_data_for_js = db.session.execute(
        select(Ingredient.title, Ingredient.title_genitive).order_by(Ingredient.title)
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
                return redirect(url_for('edit_recipe', recipe_id=recipe.id))

            recipe.title = title
            recipe.description = description

            selected_categories = db.session.execute(
                select(Category).where(Category.id.in_(category_ids))
            ).scalars().all()
            recipe.categories = list(selected_categories)

            recipe.recipe_ingredients = []
            recipe.instructions = []
            recipe.tips = []
            db.session.flush()

            amounts = request.form.getlist('amount')
            measures = request.form.getlist('measure')
            ingredient_titles_input = request.form.getlist('ingredient_title')
            ingredient_titles_genitive = request.form.getlist('ingredient_title_genitive')

            for i in range(len(ingredient_titles_input)):
                title_input = ingredient_titles_input[i].strip()
                if not title_input:
                    continue

                amount_str = amounts[i].strip() if i < len(amounts) and amounts[i] else None
                measure = measures[i].strip() if i < len(measures) and measures[i] else None
                title_gen_input = ingredient_titles_genitive[i].strip() if i < len(ingredient_titles_genitive) and \
                                                                           ingredient_titles_genitive[i] else None

                existing_ingredient = db.session.execute(
                    select(Ingredient).where(Ingredient.title == title_input)
                ).scalar_one_or_none()

                if existing_ingredient is None:
                    existing_ingredient = Ingredient(
                        title=title_input,
                        title_genitive=title_gen_input or title_input
                    )
                    db.session.add(existing_ingredient)
                    db.session.flush()

                recipe_ingredient = RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=existing_ingredient.id,
                    amount=convert_amount(amount_str),
                    measure=measure
                )
                db.session.add(recipe_ingredient)

            instruction_descriptions = request.form.getlist('instruction_description')
            step_orders = request.form.getlist('step_order')

            for i in range(len(instruction_descriptions)):
                step_desc = instruction_descriptions[i].strip()
                if step_desc:
                    step = InstructionStep(
                        recipe_id=recipe.id,
                        description=step_desc,
                        step_order=int(step_orders[i]) if i < len(step_orders) else (i + 1)
                    )
                    db.session.add(step)

            tip_descriptions = request.form.getlist('tip_description')
            for tip_text in tip_descriptions:
                text = tip_text.strip()
                if text:
                    new_tip = RecipeTip(
                        recipe_id=recipe.id,
                        text=text
                    )
                    db.session.add(new_tip)

            db.session.commit()
            flash('Рецепт успішно оновлено!', 'success')
            return redirect(url_for('recipe', recipe_id=recipe.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Помилка при оновленні рецепту: {e}', 'danger')
            return redirect(url_for('edit_recipe', recipe_id=recipe.id))

    return render_template(
        'edit_recipe.html',  # Або add_recipe.html, якщо ви зробите його універсальним
        recipe=recipe,
        categories=all_categories,
        ingredient_titles_json=ingredient_titles
    )


@app.route('/recipe/<int:recipe_id>/delete', methods=['POST'])
@login_required
def delete_recipe(recipe_id):
    recipe = db.get_or_404(Recipe, recipe_id)
    db.session.delete(recipe)
    db.session.commit()
    flash('Рецепт видалено.', 'info')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=False)
