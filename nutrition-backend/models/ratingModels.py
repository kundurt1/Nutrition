from pydantic import BaseModel,Field
from typing import Optional, List

class RateRecipeRequest(BaseModel):
    user_id: str = Field(..., description="User UUID")
    recipe_id: str = Field(..., description="Recipe UUID")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    notes: Optional[str] = Field(None, max_length=1000)

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