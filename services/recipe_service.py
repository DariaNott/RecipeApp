import models
import schemas
from fastapi import HTTPException, status
from repos.recipe_repo import RecipeRepository
from repos.category_repo import CategoryRepository


class RecipeService:
    def __init__(self, recipe_repo: RecipeRepository, category_repo: CategoryRepository):
        self.recipe_repo = recipe_repo
        self.category_repo = category_repo

    async def get_all_recipes(self) -> list[models.Recipe]:
        return await self.recipe_repo.list_all_with_details()

    async def create_recipe(self, recipe_data: schemas.RecipeCreate) -> models.Recipe:
        assigned_categories: list[models.Category] = []
        if recipe_data.category_names:
            for cat_name in recipe_data.category_names:
                category = await self.category_repo.get_by_name(cat_name)
                if not category:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Category with name '{cat_name}' not found. Create it first.",
                    )
                assigned_categories.append(category)

        assigned_ingredients: list[models.RecipeIngredient] = []
        if recipe_data.ingredients:
            for ing in recipe_data.ingredients:
                assigned_ingredients.append(
                    models.RecipeIngredient(name=ing.name, amount=ing.amount)
                )

        assigned_instructions: list[models.RecipeInstruction] = []
        if recipe_data.instructions:
            for step in recipe_data.instructions:
                assigned_instructions.append(
                    models.RecipeInstruction(step=step.step, text=step.text)
                )

        assigned_tips: list[models.RecipeTip] = []
        if recipe_data.tips:
            for tip in recipe_data.tips:
                assigned_tips.append(models.RecipeTip(text=tip.text))

        new_recipe = models.Recipe(
            title=recipe_data.title,
            description=recipe_data.description,
            categories=assigned_categories,
            ingredients=assigned_ingredients,
            instructions=assigned_instructions,
            tips=assigned_tips,
        )

        try:
            return await self.recipe_repo.create(new_recipe)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Recipe not saved. Error: {str(e)}",
            )

    async def get_recipe_by_id(self, recipe_id: int) -> models.Recipe:
        recipe = await self.recipe_repo.get_by_id_with_details(recipe_id)
        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recipe with ID {recipe_id} not found",
            )
        return recipe

    async def update_recipe(self, recipe_id: int, recipe_data: schemas.RecipeCreate) -> models.Recipe:
        db_recipe = await self.recipe_repo.get_by_id_with_details(recipe_id)
        if not db_recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recipe with ID {recipe_id} not found",
            )

        db_recipe.title = recipe_data.title
        db_recipe.description = recipe_data.description

        if recipe_data.category_names is not None:
            new_categories: list[models.Category] = []
            for cat_name in recipe_data.category_names:
                category = await self.category_repo.get_by_name(cat_name)
                if not category:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Category with name '{cat_name}' not found. Create it first.",
                    )
                new_categories.append(category)
            db_recipe.categories = new_categories

        if recipe_data.ingredients is not None:
            db_recipe.ingredients.clear()
            for ing in recipe_data.ingredients:
                db_recipe.ingredients.append(
                    models.RecipeIngredient(name=ing.name, amount=ing.amount)
                )

        if recipe_data.instructions is not None:
            db_recipe.instructions.clear()
            for step in recipe_data.instructions:
                db_recipe.instructions.append(
                    models.RecipeInstruction(step=step.step, text=step.text)
                )

        if recipe_data.tips is not None:
            db_recipe.tips.clear()
            for tip in recipe_data.tips:
                db_recipe.tips.append(models.RecipeTip(text=tip.text))

        try:
            await self.recipe_repo.commit_and_refresh(db_recipe)
            return db_recipe
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Couldn't update the recipe. Error: {str(e)}",
            )

    async def delete_recipe(self, recipe_id: int) -> None:
        recipe = await self.recipe_repo.get_by_id(recipe_id)
        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipe not found.",
            )
        await self.recipe_repo.delete_by_id(recipe_id)
        return None