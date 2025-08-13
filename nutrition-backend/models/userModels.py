from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date

class LogMealRequest(BaseModel):
    user_id: str = Field(..., description="User UUID")
    recipe_data: Dict[str, Any] = Field(..., description="Recipe data to log")
    date: Optional[str] = Field(None, description="Date to log meal (YYYY-MM-DD)")
    meal_type: Optional[str] = Field("dinner", description="Type of meal")

class CustomEntryRequest(BaseModel):
    user_id: str = Field(..., description="User UUID")
    food_name: str = Field(..., min_length=1, max_length=200)
    calories: float = Field(..., gt=0, description="Calories per serving")
    protein: Optional[float] = Field(0, ge=0, description="Protein in grams")
    carbs: Optional[float] = Field(0, ge=0, description="Carbs in grams")
    fat: Optional[float] = Field(0, ge=0, description="Fat in grams")
    servings: Optional[float] = Field(1, gt=0, description="Number of servings")
    fiber: Optional[float] = Field(0, ge=0, description="Fiber in grams")
    date: Optional[str] = Field(None, description="Date to log (YYYY-MM-DD)")
