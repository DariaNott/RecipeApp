from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class RecipeIngredientBase(BaseModel):
    name: str
    amount: Optional[str] = None

class RecipeIngredientResponse(RecipeIngredientBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class RecipeInstructionBase(BaseModel):
    step: int
    text: str

class RecipeInstructionResponse(RecipeInstructionBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class CategoryResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class RecipeBase(BaseModel):
    title: str
    description: Optional[str] = None

class RecipeCreate(RecipeBase):
    category_names: List[str]
    ingredients: List[RecipeIngredientBase]
    instructions: List[RecipeInstructionBase]

class RecipeResponse(RecipeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class RecipeTipBase(BaseModel):
    text: str

class RecipeTipResponse(RecipeTipBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class RecipeDetailResponse(RecipeResponse):
    categories: List[CategoryResponse]
    ingredients: List[RecipeIngredientResponse]
    instructions: List[RecipeInstructionResponse]
    tips: List[RecipeTipResponse]