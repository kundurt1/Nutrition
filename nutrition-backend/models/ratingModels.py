from pydantic import BaseModel
from typing import Optional, List

class RateRecipeRequest(BaseModel):
    user_id: str
    recipe_id: Optional[str] = None
    recipe_data: Optional[dict] = None
    rating: int
    feedback_reason: Optional[str] = None

class AddFavoriteRequest(BaseModel):
    user_id: str
    recipe_id: Optional[str] = None
    recipe_data: Optional[dict] = None
    recipe_name: str
    notes: Optional[str] = None

class CreateCollectionRequest(BaseModel):
    user_id: str
    name: str
    description: Optional[str] = None