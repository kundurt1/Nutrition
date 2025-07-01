from fastapi import APIRouter, HTTPException
from models.ratingModels import RateRecipeRequest

router = APIRouter()

@router.post("/rate-recipe")
def rate_recipe(req: RateRecipeRequest):
    """Rate a recipe and update preferences - used by RecipeRatings.jsx"""
    try:
        return {"message": "Rate recipe endpoint working", "rating": req.rating}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit rating: {str(e)}")

@router.get("/user-preferences/{user_id}")
def get_user_preferences(user_id: str):
    """Get user's learned preferences - used for smart recipe generation"""
    try:
        return {"message": "Get preferences endpoint working", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get preferences: {str(e)}")

@router.get("/recipe-ratings/{user_id}")
def get_user_recipe_ratings(user_id: str, limit: int = 50):
    """Get user's rating history - used by ratings analytics"""
    try:
        return {"message": "Get ratings endpoint working", "user_id": user_id, "limit": limit}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ratings: {str(e)}")