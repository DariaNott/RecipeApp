from sqlalchemy import Table, Column, Integer, String, ForeignKey, Float, DateTime, func, select
from sqlalchemy.orm import Mapped, relationship, mapped_column
from typing import List, Optional
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

db = SQLAlchemy()

recipe_category_association = Table(
    'recipe_category_association',
    db.metadata,
    Column('recipe_id', ForeignKey('recipe.id'), primary_key=True),
    Column('category_id', ForeignKey('category.id'), primary_key=True)
)

# Допоміжна таблиця для зв'язку
class RecipeIngredient(db.Model):
    __tablename__ = 'recipe_ingredient'

    recipe_id: Mapped[int] = mapped_column(ForeignKey('recipe.id'), primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey('ingredient.id'), primary_key=True)

    amount: Mapped[Optional[float]] = mapped_column(db.Float, nullable=True)
    measure: Mapped[Optional[str]] = mapped_column(db.String(20), nullable=True)

    recipe: Mapped['Recipe'] = relationship(back_populates='recipe_ingredients')
    ingredient: Mapped['Ingredient'] = relationship(back_populates='recipe_ingredients')

    def __repr__(self):
        return f"<RecipeIngredient ingredient_id={self.ingredient_id} amount={self.amount} measure='{self.measure}'>"


# Модель для кроків інструкції
class InstructionStep(db.Model):
    __tablename__ = 'instruction_step'

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)

    # FK до рецепта
    recipe_id: Mapped[int] = mapped_column(ForeignKey('recipe.id'))

    # Текст самого кроку
    description: Mapped[str] = mapped_column(db.Text)

    # ****** КЛЮЧОВЕ ПОЛЕ ******
    # Це поле зберігає порядок (1, 2, 3...)
    step_order: Mapped[int] = mapped_column(db.Integer)

    # Зв'язок до рецепта
    recipe: Mapped['Recipe'] = relationship(back_populates='instructions')

    def __repr__(self):
        return f"<InstructionStep order={self.step_order} recipe_id={self.recipe_id}>"


# Таблиця Рецептів
class Recipe(db.Model):
    __tablename__ = 'recipe'

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    title: Mapped[str] = mapped_column(db.String(255))
    description: Mapped[str] = mapped_column(db.Text)
    created_date: Mapped[DateTime] = mapped_column(
        db.DateTime,
        default=db.func.now()
    )
    # Зв'язок до нової таблиці InstructionStep
    # order_by=InstructionStep.step_order ГАРАНТУЄ правильний порядок при отриманні
    instructions: Mapped[List[InstructionStep]] = relationship(
        back_populates='recipe',
        order_by=InstructionStep.step_order,
        cascade='all, delete-orphan'
    )

    # Зв'язок до допоміжної таблиці
    recipe_ingredients: Mapped[List[RecipeIngredient]] = relationship(
        back_populates='recipe', cascade='all, delete-orphan'
    )

    # Зв'язок до Category
    categories: Mapped[List['Category']] = relationship(
        secondary=recipe_category_association,
        back_populates='recipes'
    )

    def __repr__(self):
        return f"<Recipe title='{self.title}'>"


#  Таблиця Ingredient
class Ingredient(db.Model):
    __tablename__ = 'ingredient'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(unique=True)  # Унікальна назва
    title_genitive = db.Column(db.String(120), nullable=True)

    # Зв'язок до допоміжної таблиці
    recipe_ingredients: Mapped[List[RecipeIngredient]] = relationship(
        back_populates='ingredient', cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<Ingredient title='{self.title}'>"


# Таблиця Category
class Category(db.Model):
    __tablename__ = 'category'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(unique=True)

    # ****** ПОЛЯ ДЛЯ ІЄРАРХІЇ ******

    # 1. parent_id: FK, що посилається на id цієї ж таблиці (category.id)
    # Optional[int] дозволяє полю бути NULL (тобто це категорія верхнього рівня)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('category.id'),
        nullable=True  # Дозволяємо бути NULL для головних категорій
    )

    # 2. parent: Зв'язок до батьківської категорії (батько може бути лише один)
    parent: Mapped[Optional['Category']] = relationship(
        remote_side=[id],  # Вказуємо, що id є "віддаленою" стороною
        back_populates='children'
    )

    # 3. children: Зворотний зв'язок до дочірніх категорій (дітей може бути багато)
    # Цей зв'язок дозволить нам легко отримати всі підкатегорії (наприклад, Гарніри, М'ясо)
    # з категорії Основні страви.
    children: Mapped[List['Category']] = relationship(
        back_populates='parent',
        cascade='all, delete-orphan',
        order_by='Category.title' # Сортуємо для порядку
    )

    recipes: Mapped[List['Recipe']] = relationship(
        secondary=recipe_category_association,
        back_populates='categories'
    )

    def __repr__(self):
        return f"<Category title='{self.title}' parent_id={self.parent_id}>"



# --- Функція для початкового заповнення бази даних ---
def seed_data(app):
    """
    Заповнює базу даних початковими даними: категоріями, інгредієнтами та рецептами.
    """
    with app.app_context():
        category_count = db.session.scalar(
            select(func.count()).select_from(Category)
        )

        if category_count > 0:
            logging.info("Початкові дані вже існують (знайдено категорій: %s). Сідування пропущено.", category_count)
            return

        print("Заповнення бази даних початковими даними...")

        try:
            # 1. Create Parent categories(parent_id = NULL)
            breakfasts = Category(title='Сніданки')
            soups = Category(title='Супи')
            salads = Category(title='Салати')
            main_dishes = Category(title='Основні страви')
            world_cuisine = Category(title='Кухні світу')
            desserts = Category(title='Десерти')
            snack = Category(title='Перекус')
            sauce = Category(title='Соуси')
            drinks = Category(title='Напої')
            hot_dishes = Category(title='Гострі страви')
            holiday_dishes = Category(title='Святкові страви')

            db.session.add_all([breakfasts, soups, salads, main_dishes, world_cuisine, desserts, snack, sauce, drinks,
                                hot_dishes, holiday_dishes])
            db.session.flush()  # Отримуємо ID для батьківських елементів

            # 2. Create children
            garnish = Category(title='Гарніри', parent=main_dishes)
            meat = Category(title='М\'ясо', parent=main_dishes)
            fish = Category(title='Риба', parent=main_dishes)
            dough = Category(title='Страви з тіста', parent=main_dishes)
            open_fire = Category(title='Страви на вогні', parent=main_dishes)

            ukr = Category(title='Українська кухня', parent=world_cuisine)
            thai = Category(title='Тайська кухня', parent=world_cuisine)
            italian = Category(title='Італійська кухня', parent=world_cuisine)

            baking = Category(title='Випічка', parent=desserts)

            alcohol_drinks = Category(title='Алкогольні напої', parent=drinks)
            nonalcohol_drinks = Category(title='Безалкогольні напої', parent=drinks)
            hot_drinks = Category(title='Гарячі напої', parent=drinks)
            cold_drinks = Category(title='Холодні напої', parent=drinks)

            easter = Category(title=' Великодні страви', parent=holiday_dishes)

            db.session.add_all([garnish, meat, fish, dough, open_fire, ukr, thai, italian, baking, alcohol_drinks,
                                nonalcohol_drinks, hot_drinks, cold_drinks, easter])
            db.session.flush()

            # 3. Create Ingredients
            ingredients_list = []
            # 3. Create Ingredients
            minced_beef = Ingredient(title='Яловичий фарш', title_genitive="Яловичого фаршу")
            ingredients_list.append(minced_beef)
            tomatoes = Ingredient(title='Томати', title_genitive='Томатів')
            ingredients_list.append(tomatoes)
            tomato_paste = Ingredient(title='Томатна паста', title_genitive='Томатної пасти')
            ingredients_list.append(tomato_paste)
            sugar = Ingredient(title='Цукор', title_genitive='Цукру')
            ingredients_list.append(sugar)
            spices = Ingredient(title='Спеції за смаком', title_genitive='Спецій за смаком')
            ingredients_list.append(spices)
            salt = Ingredient(title='Сіль', title_genitive='Солі')
            ingredients_list.append(salt)
            pepper = Ingredient(title='Перець', title_genitive='Перцю')
            ingredients_list.append(pepper)
            pumpkin = Ingredient(title='Гарбуз', title_genitive='Гарбуза')
            ingredients_list.append(pumpkin)
            potato = Ingredient(title='Картопля', title_genitive='Картоплі')
            ingredients_list.append(potato)
            carrot = Ingredient(title='Морква', title_genitive='Моркви')
            ingredients_list.append(carrot)
            milk = Ingredient(title='Молоко', title_genitive='Молока')
            ingredients_list.append(milk)

            db.session.add_all(ingredients_list)
            db.session.flush()

            # 4.1. Створення Рецепта
            step1 = InstructionStep(
                description='Почистити овочі, видалити насіння з гарбуза.',
                step_order=1)
            step2 = InstructionStep(
                description='Нарізати овочі кубіком. Картоплю нарізати крупніше ніж моркву, бо морква довше вариться. Якщо гарбуз твердий - нарізати таким же розміром як і моркву.',
                step_order=2)
            step3 = InstructionStep(description='Викласти овочі в каструлю. Залити молоком. Молоко можна розбавити водою (наприклад, 200 мл. молока, решта вода). Рідина має повністю покривати всі овочі. Посолити.',
                                    step_order=3)
            step4 = InstructionStep(
                description='Довести до кипіння на великому вогні, потім зменшити вогонь та варити ще приблизно 25 хвилин. Всі овочі мають бути м’якими.',
                step_order=4)
            step5 = InstructionStep(
                description="Коли овочі стануть м'якими, відлити більшу частину рідини в окрему чашу. Решту перебити занурювальним блендером до однорідної консистенції. Густоту крем-супу регулювати відлитою рідиною.",
                step_order=5)

            pumpkin_soup_recipe = Recipe(
                title='Гарбузовий крем-суп',
                categories=[main_dishes, soups],
                description="Ніжний та ароматний суп-пюре з гарбуза та молока.",
                instructions=[step1, step2, step3, step4, step5],
            )

            # Створення зв'язків RecipeIngredient
            ri1 = RecipeIngredient(ingredient=pumpkin, amount=300, measure='грам')
            ri2 = RecipeIngredient(ingredient=potato, amount=2, measure='шт.')
            ri3 = RecipeIngredient(ingredient=carrot, amount=1, measure='шт.')
            ri4 = RecipeIngredient(ingredient=milk, amount=500, measure="мл.")
            ri5 = RecipeIngredient(ingredient=salt)
            ri6 = RecipeIngredient(ingredient=pepper)

            pumpkin_soup_recipe.recipe_ingredients.extend([ri1, ri2, ri3, ri4, ri5, ri6])
            db.session.add(pumpkin_soup_recipe)

            step1 = InstructionStep(
                description='Підготувати фарш. Додати сіль, перець, спеції за бажанням (сухий часник, чебрець, папріка, чи будь які інші за смаком).',
                step_order=1)
            step2 = InstructionStep(
                description='Нарізати томати на невеликі шматочки. Розігріти сковорідку з оливковою олією.',
                step_order=2)
            step3 = InstructionStep(description='Обсмажити томати на середньому або малому вогні щоб ті пустили сік.',
                                    step_order=3)
            step4 = InstructionStep(
                description='Додати томатну пасту. Перемішати. Додати спеції. Трошки обсмажити. Якщо соус виходе загустий додати води.',
                step_order=4)
            step5 = InstructionStep(
                description='Спробувати соус, якщо кислий - балансувати смак цукром. Виключити вогонь по готовності смаку та консистенції.',
                step_order=5)
            step6 = InstructionStep(description='Розігріти духовку до 180°С.', step_order=6)
            step7 = InstructionStep(description='Зробити невелики кульки х фаршу та викласти в ємність для запікання.',
                                    step_order=7)
            step8 = InstructionStep(description="Залити м'ясні кульки томатним соусом. Запікати 25-30 хвилин.",
                                    step_order=8)

            meatball_recipe = Recipe(
                title='Мітболи',
                categories=[main_dishes, meat, sauce],
                description="Соковиті мітболи з яловичини в томатному соусі.",
                instructions=[step1, step2, step3, step4, step5, step6, step7, step8],
            )

            # Створення зв'язків RecipeIngredient
            ri1 = RecipeIngredient(ingredient=minced_beef, amount=800, measure='грам')
            ri2 = RecipeIngredient(ingredient=tomatoes, amount=400, measure='грам')
            ri3 = RecipeIngredient(ingredient=tomato_paste, amount=50, measure='грам')
            ri4 = RecipeIngredient(ingredient=sugar)
            ri5 = RecipeIngredient(ingredient=spices)
            ri6 = RecipeIngredient(ingredient=salt)
            ri7 = RecipeIngredient(ingredient=pepper)

            meatball_recipe.recipe_ingredients.extend([ri1, ri2, ri3, ri4, ri5, ri6, ri7])
            db.session.add(meatball_recipe)

            # Фіксація всіх змін
            db.session.commit()
            print("✅ База даних успішно заповнена.")

        except IntegrityError as e:
            logging.error("🛑 Помилка цілісності бази даних під час сідування.")

            logging.error(f"SQLAlchemy Error: {e.orig}")
            if hasattr(e, 'statement'):
                logging.error(f"SQL Statement: {e.statement}")

            if hasattr(e, 'params'):
                logging.error(f"SQL Params: {e.params}")
            db.session.rollback()