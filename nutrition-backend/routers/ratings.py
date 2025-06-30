from fastapi import APIRouter, HTTPException
from models.rating_models import RateRecipeRequest
from services.rating_service import RatingService

router = APIRouter()
rating_service = RatingService()

@router.post("/rate-recipe")
async def rate_recipe(req: RateRecipeRequest):
    """Rate a recipe and update preferences - used by RecipeRatings.jsx"""
    try:
        return await rating_service.rate_recipe(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit rating: {str(e)}")

@router.get("/user-preferences/{user_id}")
async def get_user_preferences(user_id: str):
    """Get user's learned preferences - used for smart recipe generation"""
    try:
        return await rating_service.get_user_preferences(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get preferences: {str(e)}")

@router.get("/recipe-ratings/{user_id}")
async def get_user_recipe_ratings(user_id: str, limit: int = 50):
    """Get user's rating history - used by ratings analytics"""
    try:
        return await rating_service.get_user_recipe_ratings(user_id, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ratings: {str(e)}")