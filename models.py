from sqlalchemy import Table, Column, Integer, String, ForeignKey, Float, DateTime, func, select
from sqlalchemy.orm import Mapped, relationship, mapped_column
from typing import List, Optional
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

db = SQLAlchemy()

recipe_category_association = Table(
    'recipe_category_association',
    db.metadata,
    Column('recipe_id', ForeignKey('recipe.id'), primary_key=True),
    Column('category_id', ForeignKey('category.id'), primary_key=True)
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


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


class InstructionStep(db.Model):
    __tablename__ = 'instruction_step'

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey('recipe.id'))
    description: Mapped[str] = mapped_column(db.Text)
    step_order: Mapped[int] = mapped_column(db.Integer)
    recipe: Mapped['Recipe'] = relationship(back_populates='instructions')

    def __repr__(self):
        return f"<InstructionStep order={self.step_order} recipe_id={self.recipe_id}>"


class RecipeTip(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(db.Text, nullable=False)
    recipe_id: Mapped[int] = mapped_column(db.ForeignKey("recipe.id"))

    recipe: Mapped["Recipe"] = relationship(back_populates="tips")

class Recipe(db.Model):
    __tablename__ = 'recipe'

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    title: Mapped[str] = mapped_column(db.String(255))
    description: Mapped[str] = mapped_column(db.Text)
    tips: Mapped[List["RecipeTip"]] = relationship(back_populates="recipe", cascade="all, delete-orphan")
    created_date: Mapped[DateTime] = mapped_column(
        db.DateTime,
        default=db.func.now()
    )

    instructions: Mapped[List[InstructionStep]] = relationship(
        back_populates='recipe',
        order_by=InstructionStep.step_order,
        cascade='all, delete-orphan'
    )

    recipe_ingredients: Mapped[List[RecipeIngredient]] = relationship(
        back_populates='recipe', cascade='all, delete-orphan'
    )

    categories: Mapped[List['Category']] = relationship(
        secondary=recipe_category_association,
        back_populates='recipes'
    )

    def __repr__(self):
        return f"<Recipe title='{self.title}'>"


class Ingredient(db.Model):
    __tablename__ = 'ingredient'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(unique=True)  # Унікальна назва
    title_genitive = db.Column(db.String(120), nullable=True)

    recipe_ingredients: Mapped[List[RecipeIngredient]] = relationship(
        back_populates='ingredient', cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<Ingredient title='{self.title}'>"


class Category(db.Model):
    __tablename__ = 'category'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(unique=True)

    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('category.id'),
        nullable=True  # Дозволяємо бути NULL для головних категорій
    )

    parent: Mapped[Optional['Category']] = relationship(
        remote_side=[id],  # Вказуємо, що id є "віддаленою" стороною
        back_populates='children'
    )

    children: Mapped[List['Category']] = relationship(
        back_populates='parent',
        cascade='all, delete-orphan',
        order_by='Category.title'  # Сортуємо для порядку
    )

    recipes: Mapped[List['Recipe']] = relationship(
        secondary=recipe_category_association,
        back_populates='categories'
    )

    def __repr__(self):
        return f"<Category title='{self.title}' parent_id={self.parent_id}>"
