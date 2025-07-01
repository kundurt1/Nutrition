from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from models.ratingModels import AddFavoriteRequest, CreateCollectionRequest
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

        # Check if already favorited
        existing_check = supabase.table("favorites") \
            .select("id") \
            .eq("user_id", req.user_id)

        if req.recipe_id:
            existing_check = existing_check.eq("recipe_id", req.recipe_id)
        else:
            existing_check = existing_check.eq("recipe_name", req.recipe_name)

        existing_result = existing_check.execute()

        if existing_result.data and len(existing_result.data) > 0:
            return {
                "success": False,
                "message": "Recipe is already in favorites",
                "favorite_id": existing_result.data[0]["id"]
            }

        # Add to favorites
        favorite_data = {
            "user_id": req.user_id,
            "recipe_name": req.recipe_name,
            "notes": req.notes,
            "favorited_at": datetime.now().isoformat()
        }

        if req.recipe_id:
            favorite_data["recipe_id"] = req.recipe_id
        else:
            favorite_data["recipe_data"] = req.recipe_data

        insert_result = supabase.table("favorites").insert(favorite_data).execute()

        if insert_result.data and len(insert_result.data) > 0:
            favorite_id = insert_result.data[0]["id"]
            print(f"✅ Added '{req.recipe_name}' to favorites for user {req.user_id}")
            
            return {
                "success": True,
                "message": "Recipe added to favorites",
                "favorite_id": favorite_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add favorite")

    except Exception as e:
        print(f"❌ Error in add_favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add favorite: {str(e)}")

@router.delete("/remove-favorite/{favorite_id}")
def remove_favorite(favorite_id: str, user_id: str = Query(...)):
    """Remove from favorites - used by Favorites.jsx"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        result = supabase.table("favorites") \
            .delete() \
            .eq("id", favorite_id) \
            .eq("user_id", user_id) \
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

        query = supabase.table("favorites") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("favorited_at", desc=True)

        if collection_id:
            query = query.eq("collection_id", collection_id)

        if limit:
            query = query.limit(limit)

        result = query.execute()

        favorites = result.data or []

        # Get total count for pagination
        count_result = supabase.table("favorites") \
            .select("id", count="exact") \
            .eq("user_id", user_id)

        if collection_id:
            count_result = count_result.eq("collection_id", collection_id)

        count_query = count_result.execute()
        total_count = count_query.count if hasattr(count_query, 'count') else len(favorites)

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

        query = supabase.table("favorites") \
            .select("id") \
            .eq("user_id", user_id)

        if recipe_id:
            query = query.eq("recipe_id", recipe_id)
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
            "user_id": req.user_id,
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
            .eq("user_id", user_id) \
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

# Update routers/ratings.py with full database functionality
# Create a new file or update existing ratings.py

# routers/ratings.py
from fastapi import APIRouter, HTTPException
from models.ratingModels import RateRecipeRequest
from database import supabase
from datetime import datetime
import uuid

router = APIRouter()

def update_user_preferences_from_rating(user_id: str, rating: int, feedback_reason: str, recipe_data: dict):
    """Analyze the rating and feedback to update user preferences"""
    try:
        if not supabase:
            return False

        # Get current preferences or create new ones
        current_prefs = supabase.table("user_preference_patterns") \
            .select("*") \
            .eq("user_id", user_id) \
            .limit(1) \
            .execute()
        
        if current_prefs.data and len(current_prefs.data) > 0:
            prefs = current_prefs.data[0]
            disliked_ingredients = prefs.get("disliked_ingredients", [])
            disliked_cuisines = prefs.get("disliked_cuisines", [])
            preferred_ingredients = prefs.get("preferred_ingredients", [])
            preferred_cuisines = prefs.get("preferred_cuisines", [])
        else:
            disliked_ingredients = []
            disliked_cuisines = []
            preferred_ingredients = []
            preferred_cuisines = []

        # If rating is low (1-2), analyze what to avoid
        if rating <= 2:
            recipe_ingredients = [ing.get("name", "").lower() for ing in recipe_data.get("ingredients", [])]
            recipe_cuisine = recipe_data.get("cuisine", "").lower()
            
            if feedback_reason == "Too many ingredients I don't like":
                for ingredient in recipe_ingredients:
                    if ingredient and ingredient not in disliked_ingredients:
                        disliked_ingredients.append(ingredient)
                        
            elif feedback_reason == "Don't like this cuisine":
                if recipe_cuisine and recipe_cuisine not in disliked_cuisines:
                    disliked_cuisines.append(recipe_cuisine)
        
        # If rating is high (4-5), add to preferred
        elif rating >= 4:
            recipe_ingredients = [ing.get("name", "").lower() for ing in recipe_data.get("ingredients", [])]
            recipe_cuisine = recipe_data.get("cuisine", "").lower()
            
            for ingredient in recipe_ingredients[:3]:  # Top 3 ingredients
                if ingredient and ingredient not in preferred_ingredients and ingredient not in disliked_ingredients:
                    preferred_ingredients.append(ingredient)
                    
            if recipe_cuisine and recipe_cuisine not in preferred_cuisines:
                preferred_cuisines.append(recipe_cuisine)

        # Update or insert preferences
        preference_data = {
            "user_id": user_id,
            "disliked_ingredients": disliked_ingredients[-20:],  # Keep last 20
            "disliked_cuisines": disliked_cuisines[-10:],
            "preferred_ingredients": preferred_ingredients[-20:],
            "preferred_cuisines": preferred_cuisines[-10:],
            "updated_at": datetime.now().isoformat()
        }
        
        if current_prefs.data:
            supabase.table("user_preference_patterns") \
                .update(preference_data) \
                .eq("user_id", user_id) \
                .execute()
        else:
            supabase.table("user_preference_patterns") \
                .insert(preference_data) \
                .execute()
                
        return True
        
    except Exception as e:
        print(f"Error updating user preferences: {e}")
        return False

@router.post("/rate-recipe")
def rate_recipe(req: RateRecipeRequest):
    """Rate a recipe and update preferences - used by RecipeRatings.jsx"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Validate rating
        if req.rating < 1 or req.rating > 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
            
        # For recipes that exist in database
        if req.recipe_id:
            # Check if user already rated this recipe
            existing_rating = supabase.table("recipe_ratings") \
                .select("id") \
                .eq("user_id", req.user_id) \
                .eq("recipe_id", req.recipe_id) \
                .limit(1) \
                .execute()
                
            rating_data = {
                "user_id": req.user_id,
                "recipe_id": req.recipe_id,
                "rating": req.rating,
                "feedback_reason": req.feedback_reason,
                "updated_at": datetime.now().isoformat()
            }
            
            if existing_rating.data:
                # Update existing rating
                supabase.table("recipe_ratings") \
                    .update(rating_data) \
                    .eq("id", existing_rating.data[0]["id"]) \
                    .execute()
            else:
                # Insert new rating
                rating_data["created_at"] = datetime.now().isoformat()
                supabase.table("recipe_ratings") \
                    .insert(rating_data) \
                    .execute()
                    
            # Get recipe data for preference learning
            recipe_data_result = supabase.table("recipes") \
                .select("ingredients, cuisine") \
                .eq("id", req.recipe_id) \
                .single() \
                .execute()
                
            if recipe_data_result.data:
                update_user_preferences_from_rating(
                    req.user_id, 
                    req.rating, 
                    req.feedback_reason or "", 
                    recipe_data_result.data
                )
                
        # For generated recipes not yet in database
        elif req.recipe_data:
            update_user_preferences_from_rating(
                req.user_id,
                req.rating,
                req.feedback_reason or "",
                req.recipe_data
            )
            
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
    """Get user's learned preferences - used for smart recipe generation"""
    try:
        if not supabase:
            return {
                "preferences": {
                    "disliked_ingredients": [],
                    "disliked_cuisines": [],
                    "preferred_ingredients": [],
                    "preferred_cuisines": []
                },
                "has_preferences": False
            }

        preferences = supabase.table("user_preference_patterns") \
            .select("*") \
            .eq("user_id", user_id) \
            .limit(1) \
            .execute()
            
        if preferences.data and len(preferences.data) > 0:
            return {
                "preferences": preferences.data[0],
                "has_preferences": True
            }
        else:
            return {
                "preferences": {
                    "disliked_ingredients": [],
                    "disliked_cuisines": [],
                    "preferred_ingredients": [],
                    "preferred_cuisines": []
                },
                "has_preferences": False
            }
            
    except Exception as e:
        print(f"❌ Error getting user preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get preferences: {str(e)}")

@router.get("/recipe-ratings/{user_id}")
def get_user_recipe_ratings(user_id: str, limit: int = 50):
    """Get user's recipe rating history - used by ratings analytics"""
    try:
        if not supabase:
            return {
                "ratings": [],
                "total_ratings": 0
            }

        ratings = supabase.table("recipe_ratings") \
            .select("*, recipes(title, cuisine)") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
            
        return {
            "ratings": ratings.data or [],
            "total_ratings": len(ratings.data) if ratings.data else 0
        }
        
    except Exception as e:
        print(f"❌ Error getting recipe ratings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get ratings: {str(e)}")