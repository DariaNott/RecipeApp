from typing import List, Optional
from sqlalchemy import String, Integer, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from database import Base


class RecipeCategory(Base):
    __tablename__ = "recipe_categories"

    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))

    parent: Mapped[Optional["Category"]] = relationship("Category", remote_side=[id], back_populates="children")
    children: Mapped[List["Category"]] = relationship("Category", back_populates="parent")

    recipes: Mapped[List["Recipe"]] = relationship(
        "Recipe", secondary="recipe_categories", back_populates="categories"
    )


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255, collation="NOCASE"), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    categories: Mapped[List["Category"]] = relationship(
        "Category", secondary="recipe_categories", back_populates="recipes"
    )

    ingredients: Mapped[List["RecipeIngredient"]] = relationship(
        "RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan"
    )

    instructions: Mapped[List["RecipeInstruction"]] = relationship(
        "RecipeInstruction", back_populates="recipe", cascade="all, delete-orphan"
    )

    tips: Mapped[List["RecipeTip"]] = relationship(
        "RecipeTip", back_populates="recipe", cascade="all, delete-orphan"
    )


class RecipeTip(Base):
    __tablename__ = "recipe_tips"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))

    text: Mapped[str] = mapped_column(Text, nullable=False)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="tips")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    amount: Mapped[str] = mapped_column(String(50), nullable=True)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="ingredients")


class RecipeInstruction(Base):
    __tablename__ = "recipe_instructions"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id", ondelete="CASCADE"))

    step: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="instructions")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
