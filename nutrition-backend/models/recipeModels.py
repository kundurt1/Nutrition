from pydantic import BaseModel
from typing import Optional, List

class RecipeRequest(BaseModel):
    title: str
    budget: float
    user_id: str

class SingleRecipeRequest(BaseModel):
    title: str
    budget: float
    user_id: str
    regenerate_single: bool = True
    exclude_recipes: Optional[list] = []

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

