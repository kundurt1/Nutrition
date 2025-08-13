from pydantic import BaseModel, Field
from pydantic import field_validator  # pydantic v2
from typing import Optional, List, Dict, Any
import re

# ---------- Base models ----------

class Ingredients(BaseModel):
    name: str
    quantity: Optional[float] = Field(default=None)
    unit: Optional[str] = Field(default=None)
    cost_per_unit: Optional[float] = Field(default=None)

class RecipeModel(BaseModel):
    recipe_name: str
    ingredients: List[Ingredients] = []     # always objects
    directions: List[str] = []
    servings: Optional[int] = 4
    cost_estimate: Optional[float] = 0
    macros: Optional[Dict[str, Any]] = None
    cuisine: Optional[str] = None
    difficulty: Optional[str] = None
    # If you need times, define them here and validate here (not on the response)
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None

    @field_validator('prep_time', 'cook_time', mode='before')
    @classmethod
    def parse_time_values(cls, v):
        # Accept int, or strings like '15 minutes', '1 hour', '45 min', etc.
        if v is None:
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            if not s:
                return None
            # hours
            m = re.search(r'(\d+(?:\.\d+)?)\s*(?:hour|hr|hrs)', s)
            if m:
                return int(float(m.group(1)) * 60)
            # minutes
            m = re.search(r'(\d+(?:\.\d+)?)\s*(?:minute|min|mins)', s)
            if m:
                return int(float(m.group(1)))
            # bare number
            m = re.search(r'(\d+(?:\.\d+)?)', s)
            if m:
                return int(float(m.group(1)))
        return None

# ---------- Request models ----------

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

    @field_validator('serving_sizes')
    @classmethod
    def validate_serving_sizes(cls, v: List[int]):
        if not v:
            raise ValueError("Must provide at least one serving size")
        if any(size <= 0 for size in v):
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
    # If you’re on Pydantic v2, prefer using a Literal or constr with regex.
    # Keeping this to minimize blast radius:
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

# ---------- Response models ----------

class ScaledRecipeResponse(BaseModel):
    recipe: RecipeModel               # ✅ use the defined model
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