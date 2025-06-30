from pydantic import BaseModel
from typing import Optional, List

class LogMealRequest(BaseModel):
    user_id: str
    recipe_id: str
    date: Optional[str] = None

class CustomEntryRequest(BaseModel):
    user_id: str
    food_name: str
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: Optional[float] = 0.0
    date: Optional[str] = None
