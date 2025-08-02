from pydantic import BaseModel, Field
from typing import Optional, List

class RecipeRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    user_id: str = Field(..., description="User UUID")
    budget: Optional[float] = Field(None, gt=0, description="Budget in dollars")
    allergies: Optional[str] = Field(None, max_length=500)
    diet: Optional[str] = Field(None, max_length=100)

class SingleRecipeRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    user_id: str = Field(..., description="User UUID")
    exclude_recipes: Optional[List[str]] = Field([], description="Recipe names to exclude")
    budget: Optional[float] = Field(None, gt=0)
    allergies: Optional[str] = Field(None, max_length=500)
    diet: Optional[str] = Field(None, max_length=100)

class Ingredient(BaseModel):
    name: str
    quantity: float
    unit: str

class Recipe(BaseModel):
    recipe_name: str
    ingredients: List[Ingredient]
    directions: List[str]
    macros: dict
    tags: List[str]
    cuisine: str
    diet: str
    cost_estimate: float
    grocery_list: List[dict]

