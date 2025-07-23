# models/groceryModels.py - Updated with smart grocery features

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date


class GroceryItem(BaseModel):
    item_name: str
    quantity: float
    estimated_cost: Optional[float] = 0
    category: Optional[str] = "Recipe Generated"
    unit: Optional[str] = ""


class SaveGroceryListRequest(BaseModel):
    user_id: str
    grocery_items: List[GroceryItem]


class UpdateGroceryItemRequest(BaseModel):
    user_id: str
    item_id: int
    quantity: Optional[float] = None
    is_purchased: Optional[bool] = None
    estimated_cost: Optional[float] = None


# models/pantryModels.py - Complete pantry and smart grocery models

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date


class PantryItem(BaseModel):
    name: str
    category: Optional[str] = "Uncategorized"
    quantity: float = 0
    unit: Optional[str] = ""
    expiration_date: Optional[date] = None
    cost_per_unit: Optional[float] = 0
    location: Optional[str] = "Pantry"  # Pantry, Fridge, Freezer
    brand: Optional[str] = None
    notes: Optional[str] = None
    barcode: Optional[str] = None


class AddPantryItemRequest(BaseModel):
    user_id: str
    items: List[PantryItem]


class UpdatePantryItemRequest(BaseModel):
    user_id: str
    item_id: int
    quantity: Optional[float] = None
    expiration_date: Optional[date] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class ConsumePantryItemRequest(BaseModel):
    user_id: str
    item_id: int
    quantity_used: float


class SubstitutionRequest(BaseModel):
    user_id: str
    missing_ingredients: List[str]
    dietary_restrictions: Optional[List[str]] = []
    budget_preference: Optional[str] = "medium"  # low, medium, high
    cuisine_type: Optional[str] = None


class SmartGroceryListRequest(BaseModel):
    user_id: str
    recipe_ingredients: List[Dict[str, Any]]
    check_pantry: bool = True
    suggest_substitutions: bool = True
    optimize_for_budget: bool = False


class ShoppingPreferencesRequest(BaseModel):
    user_id: str
    preferred_store: Optional[str] = None
    store_layout: Optional[Dict[str, Any]] = None
    shopping_order: Optional[List[str]] = None
    budget_alerts: bool = True
    expiration_alerts: bool = True
    substitution_preferences: Optional[Dict[str, Any]] = None


class PantryAnalyticsResponse(BaseModel):
    total_items: int
    total_value: float
    expiring_soon: List[Dict[str, Any]]
    categories: Dict[str, int]
    locations: Dict[str, int]
    low_stock_items: List[Dict[str, Any]]


class SubstitutionSuggestion(BaseModel):
    original_ingredient: str
    substitute_ingredient: str
    conversion_ratio: float
    conversion_notes: str
    confidence_score: float
    cost_impact: Optional[str] = None  # lower, same, higher
    reason: str  # dietary, budget, availability
    dietary_benefits: Optional[List[str]] = []
    flavor_impact: Optional[str] = "minimal"  # minimal, slight, significant
    difficulty: Optional[str] = "easy"  # easy, moderate, challenging


class OptimizedShoppingListRequest(BaseModel):
    user_id: str
    store_name: Optional[str] = None
    optimize_by: str = "category"  # category, aisle, distance


class RecipeIngredient(BaseModel):
    name: str
    quantity: float
    unit: Optional[str] = ""
    category: Optional[str] = None
    estimated_cost: Optional[float] = 0


class MealPlanGroceryRequest(BaseModel):
    user_id: str
    meal_plans: Dict[str, List[Dict[str, Any]]]  # date -> list of meals


class WhatCanIMakeRequest(BaseModel):
    user_id: str
    max_missing_ingredients: Optional[int] = 3
    preferred_cuisine: Optional[str] = None
    dietary_restrictions: Optional[List[str]] = []
    difficulty_level: Optional[str] = None  # easy, medium, hard


class InventoryCheckRequest(BaseModel):
    user_id: str
    ingredients: List[str]


class SmartShoppingResponse(BaseModel):
    success: bool
    items_added: int
    pantry_sufficient: List[Dict[str, Any]]
    substitution_suggestions: Optional[List[Dict[str, Any]]] = []
    total_cost: float
    message: str
    optimization_applied: bool = False


class PantryInventoryResponse(BaseModel):
    items: List[Dict[str, Any]]
    analytics: PantryAnalyticsResponse


class SubstitutionResponse(BaseModel):
    substitutions: List[SubstitutionSuggestion]
    substitution_groups: List[Dict[str, Any]]
    total_suggestions: int
    ai_powered: bool


# models/mealPlanningModels.py - Extended for smart grocery integration

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date


class MealPlanEntry(BaseModel):
    recipe_name: str
    meal_type: str  # breakfast, lunch, dinner, snack
    servings: Optional[int] = 1
    prep_time: Optional[str] = None
    ingredients: Optional[List[Dict[str, Any]]] = []
    macros: Optional[Dict[str, float]] = {}


class SaveMealPlanRequest(BaseModel):
    user_id: str
    date: str  # YYYY-MM-DD format
    meals: List[MealPlanEntry]


class GenerateGroceryFromMealPlanRequest(BaseModel):
    user_id: str
    meal_plans: Dict[str, List[Dict[str, Any]]]  # date -> list of meals
    check_pantry: bool = True
    consolidate_ingredients: bool = True


class MealPlanAnalyticsRequest(BaseModel):
    user_id: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    include_nutrition: bool = True


# models/nutritionModels.py - Extended for smart integration

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date


class NutritionLogEntry(BaseModel):
    user_id: str
    food_name: str
    quantity: Optional[float] = 1
    unit: Optional[str] = "serving"
    calories: Optional[float] = 0
    protein: Optional[float] = 0
    carbs: Optional[float] = 0
    fat: Optional[float] = 0
    fiber: Optional[float] = 0
    meal_type: Optional[str] = "dinner"
    logged_at: Optional[datetime] = None


class RecipeNutritionLogRequest(BaseModel):
    user_id: str
    recipe_name: str
    macros: Dict[str, float]
    ingredients: List[Dict[str, Any]]
    servings: Optional[int] = 1


class NutritionGoalsRequest(BaseModel):
    user_id: str
    daily_calories: Optional[float] = None
    daily_protein: Optional[float] = None
    daily_carbs: Optional[float] = None
    daily_fat: Optional[float] = None
    daily_fiber: Optional[float] = None


# models/recipeModels.py - Extended for smart grocery integration

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class EnhancedRecipeRequest(BaseModel):
    title: str
    budget: float
    user_id: str
    dietary_restrictions: Optional[List[str]] = []
    cuisine_preference: Optional[str] = None
    max_prep_time: Optional[int] = None
    exclude_ingredients: Optional[List[str]] = []
    include_pantry_ingredients: bool = True


class RecipeResponse(BaseModel):
    recipe_name: str
    ingredients: List[Dict[str, Any]]
    directions: List[str]
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    servings: Optional[int] = 4
    difficulty: Optional[str] = None
    cuisine: Optional[str] = None
    macros: Optional[Dict[str, float]] = {}
    cost_estimate: float
    grocery_list: List[Dict[str, Any]]
    pantry_ingredients_used: Optional[List[str]] = []
    substitutions_made: Optional[List[Dict[str, Any]]] = []


class RegenerateRecipeRequest(BaseModel):
    title: str
    budget: float
    user_id: str
    regenerate_single: bool = False
    exclude_recipes: Optional[List[str]] = []
    keep_ingredients: Optional[List[str]] = []


class RecipeAdaptationRequest(BaseModel):
    user_id: str
    original_recipe: Dict[str, Any]
    available_ingredients: List[str]
    dietary_restrictions: Optional[List[str]] = []
    substitute_missing: bool = True


# Response Models for API consistency

class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: List[Dict[str, Any]]
    total_count: int
    page: int
    per_page: int
    has_more: bool


# models/communityModels.py - Extended for smart sharing

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ShareSmartRecipeRequest(BaseModel):
    user_id: str
    recipe_data: Dict[str, Any]
    grocery_optimizations: Optional[Dict[str, Any]] = None
    pantry_substitutions: Optional[List[Dict[str, Any]]] = []
    cost_analysis: Optional[Dict[str, Any]] = None
    sharing_level: str = "public"


class CommunitySubstitutionTip(BaseModel):
    user_id: str
    original_ingredient: str
    substitute_ingredient: str
    context: str  # recipe_name or general use case
    tip_text: str
    confidence_rating: int  # 1-5 stars
    cost_savings: Optional[float] = None


class SmartRecipeRating(BaseModel):
    user_id: str
    recipe_id: str
    overall_rating: int  # 1-5 stars
    taste_rating: Optional[int] = None
    difficulty_rating: Optional[int] = None
    cost_rating: Optional[int] = None
    grocery_convenience_rating: Optional[int] = None
    review_text: Optional[str] = None