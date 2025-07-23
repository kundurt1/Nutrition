# models/recipeScalingModels.py - Updated with flexible time validation

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
import re


# Base models
class RecipeIngredient(BaseModel):
    name: str
    quantity: float
    unit: str
    cost_per_unit: Optional[float] = 0
    category: Optional[str] = "other"


class RecipeScaling(BaseModel):
    name: str
    original_servings: int
    ingredients: List[RecipeIngredient]
    instructions: List[str]
    prep_time: int = Field(default=0, description="Prep time in minutes")
    cook_time: int = Field(default=0, description="Cook time in minutes")
    cuisine: Optional[str] = ""
    difficulty: Optional[str] = "medium"
    tags: Optional[List[str]] = []
    macros: Optional[Dict[str, Any]] = {}
    cost_estimate: Optional[float] = 0

    @validator('prep_time', 'cook_time', pre=True)
    def parse_time_values(cls, v):
        """Parse time values that might be strings like '15 minutes' or integers"""
        if isinstance(v, int):
            return v

        if isinstance(v, str):
            # Handle empty strings
            if not v.strip():
                return 30  # Default to 30 minutes for empty strings

            # Remove extra spaces and convert to lowercase
            time_str = v.strip().lower()

            # Try to extract numbers from strings like "15 minutes", "1 hour", etc.
            if 'hour' in time_str:
                hours = re.findall(r'(\d+(?:\.\d+)?)\s*(?:hour|hr)', time_str)
                if hours:
                    return int(float(hours[0]) * 60)

            if 'min' in time_str:
                minutes = re.findall(r'(\d+(?:\.\d+)?)\s*(?:minute|min)', time_str)
                if minutes:
                    return int(float(minutes[0]))

            # Try to extract just numbers
            numbers = re.findall(r'(\d+(?:\.\d+)?)', time_str)
            if numbers:
                return int(float(numbers[0]))

        # Default fallback for None or other types
        return 30


# Request models
class ScaleRecipeRequest(BaseModel):
    recipe_name: str
    new_servings: int = Field(gt=0, description="Must be greater than 0")
    user_id: str


class ConvertUnitsRequest(BaseModel):
    recipe_name: str
    unit_conversions: Dict[str, str]  # ingredient_name -> new_unit
    user_id: str


class GroceryListRequest(BaseModel):
    recipe_name: str
    servings: int = Field(gt=0, description="Must be greater than 0")
    user_id: str
    preferred_units: Optional[Dict[str, str]] = {}


class CombinedGroceryListRequest(BaseModel):
    recipe_servings: Dict[str, int]  # recipe_name -> servings
    user_id: str
    preferred_units: Optional[Dict[str, str]] = {}


class NutritionComparisonRequest(BaseModel):
    recipe_name: str
    serving_sizes: List[int] = Field(description="List of serving sizes to compare")
    user_id: str

    @validator('serving_sizes')
    def validate_serving_sizes(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Must provide at least one serving size")
        for size in v:
            if size <= 0:
                raise ValueError("All serving sizes must be greater than 0")
        return v


class OptimizeServingsRequest(BaseModel):
    recipe_name: str
    target_calories_per_serving: int = Field(gt=0, description="Target calories per serving")
    user_id: str


class BatchScaleRequest(BaseModel):
    recipe_names: List[str] = Field(min_items=1, description="At least one recipe name required")
    new_servings: int = Field(gt=0, description="Must be greater than 0")
    user_id: str


class ImportRecipeRequest(BaseModel):
    recipe_data: Dict[str, Any]
    user_id: str
    save_to_db: bool = True


class ExportRecipeRequest(BaseModel):
    recipe_name: str
    user_id: str
    format: str = Field(default="json", pattern="^(json|pdf|txt)$")


class SearchRecipesRequest(BaseModel):
    user_id: str
    query: Optional[str] = ""
    cuisine: Optional[str] = ""
    difficulty: Optional[str] = ""
    tag: Optional[str] = ""
    max_cook_time: Optional[int] = None


class UnitConversionRequest(BaseModel):
    quantity: float = Field(gt=0, description="Quantity must be positive")
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
    error: Optional[str] = None