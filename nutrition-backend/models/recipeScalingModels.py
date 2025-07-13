# nutrition-backend/models/recipeScalingModels.py

from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime

class ScaleRecipeRequest(BaseModel):
    recipe_name: str
    new_servings: int
    user_id: str

class ConvertUnitsRequest(BaseModel):
    recipe_name: str
    unit_conversions: Dict[str, str]  # ingredient_name -> new_unit
    user_id: str

class IngredientScaling(BaseModel):
    name: str
    quantity: float
    unit: str
    cost_per_unit: float = 0.0
    calories_per_unit: float = 0.0
    protein_per_unit: float = 0.0
    carbs_per_unit: float = 0.0
    fat_per_unit: float = 0.0
    fiber_per_unit: float = 0.0
    category: str = "other"

class RecipeScaling(BaseModel):
    name: str
    original_servings: int
    ingredients: List[IngredientScaling]
    instructions: List[str]
    prep_time: int = 0
    cook_time: int = 0
    cuisine: str = ""
    difficulty: str = "medium"
    tags: List[str] = []
    source: str = ""

class GroceryListRequest(BaseModel):
    recipe_name: str
    servings: int
    user_id: str
    preferred_units: Optional[Dict[str, str]] = None

class CombinedGroceryListRequest(BaseModel):
    recipe_servings: Dict[str, int]  # recipe_name -> servings
    user_id: str
    preferred_units: Optional[Dict[str, str]] = None

class NutritionComparisonRequest(BaseModel):
    recipe_name: str
    serving_sizes: List[int]
    user_id: str

class OptimizeServingsRequest(BaseModel):
    recipe_name: str
    target_calories_per_serving: float
    user_id: str

class BatchScaleRequest(BaseModel):
    recipe_names: List[str]
    new_servings: int
    user_id: str

class ImportRecipeRequest(BaseModel):
    recipe_data: Dict[str, Any]
    user_id: str
    save_to_db: bool = True

class ExportRecipeRequest(BaseModel):
    recipe_name: str
    user_id: str
    format: str = "json"  # json or csv

class SearchRecipesRequest(BaseModel):
    query: Optional[str] = ""
    cuisine: Optional[str] = None
    difficulty: Optional[str] = None
    tag: Optional[str] = None
    max_cook_time: Optional[int] = None
    user_id: str

class UnitConversionRequest(BaseModel):
    quantity: float
    from_unit: str
    to_unit: str

class RecipeAnalyticsRequest(BaseModel):
    recipe_name: str
    user_id: str

# Response models
class ScaledRecipeResponse(BaseModel):
    recipe: RecipeScaling
    scaling_factor: float
    original_servings: int
    new_servings: int

class GroceryListResponse(BaseModel):
    grocery_list: List[Dict[str, Any]]
    total_cost: float
    total_items: int
    servings: int

class NutritionComparisonResponse(BaseModel):
    comparisons: Dict[str, Dict[str, Any]]
    recipe_name: str

class RecipeAnalyticsResponse(BaseModel):
    recipe_name: str
    servings: int
    total_time: int
    cost_analysis: Dict[str, Any]
    nutrition_per_serving: Dict[str, float]
    total_nutrition: Dict[str, float]
    macro_percentages: Dict[str, float]
    ingredient_categories: List[str]
    ingredient_count: int
    cost_per_calorie: float

class UnitConversionResponse(BaseModel):
    original_quantity: float
    original_unit: str
    converted_quantity: Optional[float]
    converted_unit: str
    conversion_successful: bool
    compatible_units: List[str]