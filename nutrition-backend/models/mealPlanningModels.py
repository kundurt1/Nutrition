from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date

class SaveMealPlanRequest(BaseModel):
    user_id: str
    date: str  # YYYY-MM-DD format
    meals: List[Dict[str, Any]]  # List of meal objects

class GenerateGroceryFromMealPlanRequest(BaseModel):
    user_id: str
    meal_plans: Dict[str, List[Dict[str, Any]]]  # Date -> List of meals

class MealPlanRecipe(BaseModel):
    id: Optional[int] = None
    recipe_name: str
    cuisine: Optional[str] = "Unknown"
    cost_estimate: Optional[float] = 0.0
    prep_time: Optional[str] = "30 min"
    cook_time: Optional[str] = "20 min"
    difficulty: Optional[str] = "Medium"
    ingredients: Optional[List[Dict[str, Any]]] = []
    directions: Optional[List[str]] = []
    macros: Optional[Dict[str, Any]] = {}
    tags: Optional[List[str]] = []
    mealType: Optional[str] = "dinner"  # breakfast, lunch, dinner, snack

class UpdateMealPlanRequest(BaseModel):
    user_id: str
    date: str
    meal_id: int
    meal_type: Optional[str] = None

class DeleteMealPlanRequest(BaseModel):
    user_id: str
    date: str
    meal_id: Optional[int] = None  # If None, delete all meals for the date

class MealPlanAnalyticsRequest(BaseModel):
    user_id: str
    start_date: Optional[str] = None  # YYYY-MM-DD format
    end_date: Optional[str] = None    # YYYY-MM-DD format
    days: Optional[int] = 30