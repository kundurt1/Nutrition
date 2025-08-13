from pydantic import BaseModel, Field, conint
from typing import Optional, List, Dict, Any, Union

# ---------- Request Models ----------

class RecipeRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    user_id: str = Field(..., description="User UUID")
    budget: Optional[float] = Field(None, gt=0, description="Budget in dollars")
    allergies: Optional[str] = Field(None, max_length=500)
    diet: Optional[str] = Field(None, max_length=100)

    # New inputs
    advanced_ai: Optional[bool] = Field(True, description="Use advanced generation pipeline")
    count: conint(ge=1, le=3) = Field(3, description="How many recipes to generate (1 or 3)")

# ---------- Core Entities ----------

class Ingredient(BaseModel):
    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None

# Frontend can receive ingredients either as strings or objects,
# so we support both. (The UI normalizes to strings.)
IngredientLike = Union[str, Ingredient]

class Recipe(BaseModel):
    # Identity / naming
    id: Optional[str] = None
    recipe_name: str

    # Content
    ingredients: List[IngredientLike]
    directions: List[str]

    # Nutrition / metadata
    macros: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    cuisine: Optional[str] = None
    diet: Optional[str] = None
    difficulty: Optional[str] = None

    # Times / serving sizes (strings are fine for "10", "30", "45")
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    servings: Optional[int] = None

    # Cost and AI notes
    cost_estimate: Optional[float] = 0
    ai_insights: Optional[str] = None

    # Kept from your original model (not currently used by UI, but harmless)
    grocery_list: Optional[List[Dict[str, Any]]] = None

# ---------- Response Models ----------

class GenerateRecipeResponse(BaseModel):
    recipes: List[Recipe]
    ai_explanation: Optional[str] = None