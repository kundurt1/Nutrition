from fastapi import APIRouter, HTTPException, Query
from models.rating_models import AddFavoriteRequest, CreateCollectionRequest
from services.favorites_service import FavoritesService

router = APIRouter()
favorites_service = FavoritesService()

@router.post("/add-favorite")
async def add_favorite(req: AddFavoriteRequest):
    """Add recipe to favorites - used by RecipeRatings.jsx and Favorites.jsx"""
    try:
        return await favorites_service.add_favorite(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add favorite: {str(e)}")

@router.delete("/remove-favorite/{favorite_id}")
async def remove_favorite(favorite_id: str, user_id: str = Query(...)):
    """Remove from favorites - used by Favorites.jsx"""
    try:
        return await favorites_service.remove_favorite(favorite_id, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove favorite: {str(e)}")

@router.get("/favorites/{user_id}")
async def get_favorites(user_id: str, collection_id: Optional[str] = Query(None), limit: int = 50):
    """Get user's favorites - used by Favorites.jsx and HomePage.jsx"""
    try:
        return await favorites_service.get_favorites(user_id, collection_id, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get favorites: {str(e)}")

@router.get("/check-favorite/{user_id}")
async def check_favorite_status(
    user_id: str,
    recipe_id: Optional[str] = Query(None),
    recipe_name: Optional[str] = Query(None)
):
    """Check if recipe is favorited - used by RecipeRatings.jsx"""
    try:
        return await favorites_service.check_favorite_status(user_id, recipe_id, recipe_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check favorite status: {str(e)}")

@router.post("/create-collection")
async def create_collection(req: CreateCollectionRequest):
    """Create favorites collection - used by Favorites.jsx"""
    try:
        return await favorites_service.create_collection(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create collection: {str(e)}")

@router.get("/collections/{user_id}")
async def get_collections(user_id: str):
    """Get user's collections - used by Favorites.jsx"""
    try:
        return await favorites_service.get_collections(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get collections: {str(e)}")
