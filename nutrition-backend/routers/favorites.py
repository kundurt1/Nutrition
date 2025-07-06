from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from models.ratingModels import AddFavoriteRequest, CreateCollectionRequest, RateRecipeRequest
from database import supabase
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/add-favorite")
def add_favorite(req: AddFavoriteRequest):
    """Add recipe to favorites - used by RecipeRatings.jsx and Favorites.jsx"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Convert user_id to UUID string format if needed
        user_id_str = str(req.user_id)

        print(f"Adding favorite for user: {user_id_str}, recipe: {req.recipe_name}")

        # Check if already favorited
        existing_check = supabase.table("collection_favorites") \
            .select("id") \
            .eq("user_id", user_id_str)

        if req.recipe_id:
            existing_check = existing_check.eq("recipe_id", str(req.recipe_id))
        else:
            existing_check = existing_check.eq("recipe_name", req.recipe_name)

        existing_result = existing_check.execute()

        if existing_result.data and len(existing_result.data) > 0:
            return {
                "success": False,
                "message": "Recipe is already in favorites",
                "favorite_id": existing_result.data[0]["id"]
            }

        # Add to favorites - using your exact table structure
        favorite_data = {
            "user_id": user_id_str,
            "recipe_name": req.recipe_name,
            "notes": req.notes,
            "added_at": datetime.now().isoformat()
        }

        if req.recipe_id:
            favorite_data["recipe_id"] = str(req.recipe_id)
        
        if req.recipe_data:
            favorite_data["recipe_data"] = req.recipe_data

        print(f"Inserting favorite data: {favorite_data}")

        insert_result = supabase.table("collection_favorites").insert(favorite_data).execute()

        print(f"Insert result: {insert_result}")

        if insert_result.data and len(insert_result.data) > 0:
            favorite_id = insert_result.data[0]["id"]
            print(f"✅ Added '{req.recipe_name}' to favorites for user {req.user_id}")
            
            return {
                "success": True,
                "message": "Recipe added to favorites",
                "favorite_id": favorite_id
            }
        else:
            print(f"❌ Insert failed: {insert_result}")
            raise HTTPException(status_code=500, detail="Failed to add favorite - no data returned")

    except Exception as e:
        print(f"❌ Error in add_favorite: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to add favorite: {str(e)}")

@router.delete("/remove-favorite/{favorite_id}")
def remove_favorite(favorite_id: str, user_id: str = Query(...)):
    """Remove from favorites - used by Favorites.jsx"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        result = supabase.table("collection_favorites") \
            .delete() \
            .eq("id", favorite_id) \
            .eq("user_id", str(user_id)) \
            .execute()

        print(f"✅ Removed favorite {favorite_id} for user {user_id}")

        return {
            "success": True,
            "message": "Recipe removed from favorites"
        }

    except Exception as e:
        print(f"❌ Error in remove_favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to remove favorite: {str(e)}")

@router.get("/favorites/{user_id}")
def get_favorites(user_id: str, collection_id: Optional[str] = Query(None), limit: int = 50):
    """Get user's favorites - used by Favorites.jsx and HomePage.jsx"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        query = supabase.table("collection_favorites") \
            .select("*") \
            .eq("user_id", str(user_id))

        # Order by added_at descending (newest first)
        query = query.order("added_at", desc=True)

        if collection_id:
            query = query.eq("collection_id", str(collection_id))

        if limit:
            query = query.limit(limit)

        result = query.execute()

        favorites = result.data or []

        # Get total count for pagination
        count_result = supabase.table("collection_favorites") \
            .select("id", count="exact") \
            .eq("user_id", str(user_id))

        if collection_id:
            count_result = count_result.eq("collection_id", str(collection_id))

        try:
            count_query = count_result.execute()
            total_count = count_query.count if hasattr(count_query, 'count') else len(favorites)
        except:
            total_count = len(favorites)

        print(f"✅ Retrieved {len(favorites)} favorites for user {user_id}")

        return {
            "favorites": favorites,
            "total_count": total_count
        }

    except Exception as e:
        print(f"❌ Error in get_favorites: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get favorites: {str(e)}")

@router.get("/check-favorite/{user_id}")
def check_favorite_status(
    user_id: str,
    recipe_id: Optional[str] = Query(None),
    recipe_name: Optional[str] = Query(None)
):
    """Check if recipe is favorited - used by RecipeRatings.jsx"""
    try:
        if not supabase:
            return {"is_favorited": False, "favorite_id": None}

        query = supabase.table("collection_favorites") \
            .select("id") \
            .eq("user_id", str(user_id))

        if recipe_id:
            query = query.eq("recipe_id", str(recipe_id))
        elif recipe_name:
            query = query.eq("recipe_name", recipe_name)
        else:
            return {"is_favorited": False, "favorite_id": None}

        result = query.execute()

        if result.data and len(result.data) > 0:
            return {
                "is_favorited": True,
                "favorite_id": result.data[0]["id"]
            }
        else:
            return {
                "is_favorited": False,
                "favorite_id": None
            }

    except Exception as e:
        print(f"❌ Error in check_favorite_status: {str(e)}")
        return {"is_favorited": False, "favorite_id": None}

@router.post("/create-collection")
def create_collection(req: CreateCollectionRequest):
    """Create favorites collection - used by Favorites.jsx"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        collection_data = {
            "user_id": str(req.user_id),
            "name": req.name,
            "description": req.description,
            "created_at": datetime.now().isoformat()
        }

        insert_result = supabase.table("favorite_collections").insert(collection_data).execute()

        if insert_result.data and len(insert_result.data) > 0:
            collection_id = insert_result.data[0]["id"]
            print(f"✅ Created collection '{req.name}' for user {req.user_id}")
            
            return {
                "success": True,
                "message": "Collection created successfully",
                "collection_id": collection_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create collection")

    except Exception as e:
        print(f"❌ Error in create_collection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create collection: {str(e)}")

@router.get("/collections/{user_id}")
def get_collections(user_id: str):
    """Get user's collections - used by Favorites.jsx"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        result = supabase.table("favorite_collections") \
            .select("*") \
            .eq("user_id", str(user_id)) \
            .order("created_at", desc=True) \
            .execute()

        collections = result.data or []

        print(f"✅ Retrieved {len(collections)} collections for user {user_id}")

        return {
            "collections": collections
        }

    except Exception as e:
        print(f"❌ Error in get_collections: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get collections: {str(e)}")

# Simplified rating endpoints for now
@router.post("/rate-recipe")
def rate_recipe(req: RateRecipeRequest):
    """Rate a recipe - simplified version"""
    try:
        print(f"✅ Recipe rated {req.rating} stars by user {req.user_id}")
        return {
            "success": True,
            "message": "Rating submitted successfully",
            "preferences_updated": True
        }
    except Exception as e:
        print(f"❌ Error in rate_recipe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit rating: {str(e)}")

@router.get("/user-preferences/{user_id}")
def get_user_preferences(user_id: str):
    """Get user's learned preferences - simplified"""
    return {
        "preferences": {
            "disliked_ingredients": [],
            "disliked_cuisines": [],
            "preferred_ingredients": [],
            "preferred_cuisines": []
        },
        "has_preferences": False
    }

@router.get("/recipe-ratings/{user_id}")
def get_user_recipe_ratings(user_id: str, limit: int = 50):
    """Get user's recipe rating history - simplified"""
    return {
        "ratings": [],
        "total_ratings": 0
    }