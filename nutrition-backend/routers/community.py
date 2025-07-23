# nutrition-backend/routers/community.py

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from models.communityModels import *
from database import supabase
from datetime import datetime, timedelta
import uuid

router = APIRouter()


@router.post("/share-recipe")
def share_recipe(req: ShareRecipeRequest):
    """Share a recipe with the community"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Create shared recipe entry
        shared_recipe_data = {
            "id": str(uuid.uuid4()),
            "user_id": req.user_id,
            "recipe_data": req.recipe_data,
            "sharing_level": req.sharing_level,
            "message": req.message,
            "tags": req.tags,
            "created_at": datetime.now().isoformat(),
            "likes_count": 0,
            "comments_count": 0,
            "views_count": 0,
            "saves_count": 0
        }

        insert_result = supabase.table("shared_recipes").insert(shared_recipe_data).execute()

        if insert_result.data and len(insert_result.data) > 0:
            shared_recipe_id = insert_result.data[0]["id"]

            # Add to user's sharing history
            sharing_history_data = {
                "user_id": req.user_id,
                "shared_recipe_id": shared_recipe_id,
                "action": "shared",
                "created_at": datetime.now().isoformat()
            }

            supabase.table("user_recipe_interactions").insert(sharing_history_data).execute()

            print(f"✅ Recipe shared successfully with ID: {shared_recipe_id}")

            return {
                "success": True,
                "message": "Recipe shared successfully!",
                "shared_recipe_id": shared_recipe_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to share recipe")

    except Exception as e:
        print(f"❌ Error sharing recipe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to share recipe: {str(e)}")


@router.get("/community-feed/{user_id}")
def get_community_feed(user_id: str, page: int = Query(1), per_page: int = Query(20)):
    """Get personalized community feed for user"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        offset = (page - 1) * per_page

        # Get shared recipes with user data and interaction counts
        feed_query = supabase.table("shared_recipes") \
            .select("""
                *,
                users!inner(id, email, username, display_name, profile_image_url),
                recipe_likes!left(user_id),
                recipe_saves!left(user_id)
            """) \
            .eq("sharing_level", "public") \
            .order("created_at", desc=True) \
            .limit(per_page) \
            .offset(offset)

        result = feed_query.execute()

        if not result.data:
            return {"feed": [], "total_count": 0, "page": page}

        # Process and enrich feed data
        enriched_feed = []
        for recipe in result.data:
            # Check if current user liked/saved this recipe
            user_liked = any(like.get("user_id") == user_id for like in recipe.get("recipe_likes", []))
            user_saved = any(save.get("user_id") == user_id for save in recipe.get("recipe_saves", []))

            # Get rating average (would need additional query or denormalized data)
            rating_avg = 4.2  # Placeholder - implement actual rating calculation

            enriched_recipe = {
                "id": recipe["id"],
                "recipe_name": recipe["recipe_data"].get("recipe_name", "Shared Recipe"),
                "shared_by": {
                    "user_id": recipe["users"]["id"],
                    "username": recipe["users"].get("username", "Anonymous"),
                    "display_name": recipe["users"].get("display_name", "Community Chef"),
                    "profile_image": recipe["users"].get("profile_image_url")
                },
                "recipe_data": recipe["recipe_data"],
                "sharing_level": recipe["sharing_level"],
                "created_at": recipe["created_at"],
                "likes_count": recipe["likes_count"],
                "comments_count": recipe["comments_count"],
                "views_count": recipe.get("views_count", 0),
                "rating_average": rating_avg,
                "total_ratings": 12,  # Placeholder
                "is_liked_by_user": user_liked,
                "is_saved_by_user": user_saved,
                "tags": recipe.get("tags", []),
                "message": recipe.get("message")
            }
            enriched_feed.append(enriched_recipe)

        print(f"✅ Retrieved {len(enriched_feed)} recipes for community feed")

        return {
            "feed": enriched_feed,
            "total_count": len(enriched_feed),
            "page": page,
            "has_more": len(enriched_feed) == per_page
        }

    except Exception as e:
        print(f"❌ Error getting community feed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get community feed: {str(e)}")


@router.post("/like-recipe")
def like_recipe(shared_recipe_id: str, user_id: str):
    """Like or unlike a shared recipe"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Check if already liked
        existing_like = supabase.table("recipe_likes") \
            .select("id") \
            .eq("shared_recipe_id", shared_recipe_id) \
            .eq("user_id", user_id) \
            .execute()

        if existing_like.data and len(existing_like.data) > 0:
            # Unlike - remove the like
            supabase.table("recipe_likes") \
                .delete() \
                .eq("id", existing_like.data[0]["id"]) \
                .execute()

            # Decrement likes count
            supabase.rpc("decrement_likes_count", {"recipe_id": shared_recipe_id}).execute()

            action = "unliked"
        else:
            # Like - add the like
            like_data = {
                "shared_recipe_id": shared_recipe_id,
                "user_id": user_id,
                "created_at": datetime.now().isoformat()
            }

            supabase.table("recipe_likes").insert(like_data).execute()

            # Increment likes count
            supabase.rpc("increment_likes_count", {"recipe_id": shared_recipe_id}).execute()

            action = "liked"

        # Log the interaction
        interaction_data = {
            "user_id": user_id,
            "shared_recipe_id": shared_recipe_id,
            "action": action,
            "created_at": datetime.now().isoformat()
        }

        supabase.table("user_recipe_interactions").insert(interaction_data).execute()

        return {
            "success": True,
            "action": action,
            "message": f"Recipe {action} successfully!"
        }

    except Exception as e:
        print(f"❌ Error liking recipe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to like recipe: {str(e)}")


@router.post("/comment-recipe")
def comment_on_recipe(req: RecipeCommentRequest):
    """Add a comment to a shared recipe"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        comment_data = {
            "user_id": req.user_id,
            "shared_recipe_id": req.shared_recipe_id,
            "comment_text": req.comment_text,
            "parent_comment_id": req.parent_comment_id,
            "created_at": datetime.now().isoformat(),
            "likes_count": 0
        }

        insert_result = supabase.table("recipe_comments").insert(comment_data).execute()

        if insert_result.data and len(insert_result.data) > 0:
            # Increment comments count on shared recipe
            supabase.rpc("increment_comments_count", {"recipe_id": req.shared_recipe_id}).execute()

            comment_id = insert_result.data[0]["id"]
            print(f"✅ Comment added with ID: {comment_id}")

            return {
                "success": True,
                "message": "Comment added successfully!",
                "comment_id": comment_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add comment")

    except Exception as e:
        print(f"❌ Error adding comment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add comment: {str(e)}")


@router.get("/recipe-comments/{shared_recipe_id}")
def get_recipe_comments(shared_recipe_id: str, user_id: str = Query(...)):
    """Get comments for a shared recipe"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Get comments with user data
        comments_result = supabase.table("recipe_comments") \
            .select("""
                *,
                users!inner(id, username, display_name, profile_image_url)
            """) \
            .eq("shared_recipe_id", shared_recipe_id) \
            .order("created_at", desc=True) \
            .execute()

        comments = []
        for comment in (comments_result.data or []):
            comment_data = {
                "id": comment["id"],
                "comment_text": comment["comment_text"],
                "created_at": comment["created_at"],
                "likes_count": comment.get("likes_count", 0),
                "parent_comment_id": comment.get("parent_comment_id"),
                "user": {
                    "user_id": comment["users"]["id"],
                    "username": comment["users"].get("username", "Anonymous"),
                    "display_name": comment["users"].get("display_name", "Community Chef"),
                    "profile_image": comment["users"].get("profile_image_url")
                }
            }
            comments.append(comment_data)

        print(f"✅ Retrieved {len(comments)} comments for recipe {shared_recipe_id}")

        return {
            "comments": comments,
            "total_count": len(comments)
        }

    except Exception as e:
        print(f"❌ Error getting comments: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get comments: {str(e)}")


@router.post("/follow-user")
def follow_user(req: FollowUserRequest):
    """Follow or unfollow a user"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        if req.follower_id == req.following_id:
            raise HTTPException(status_code=400, detail="Cannot follow yourself")

        # Check if already following
        existing_follow = supabase.table("user_follows") \
            .select("id") \
            .eq("follower_id", req.follower_id) \
            .eq("following_id", req.following_id) \
            .execute()

        if existing_follow.data and len(existing_follow.data) > 0:
            # Unfollow
            supabase.table("user_follows") \
                .delete() \
                .eq("id", existing_follow.data[0]["id"]) \
                .execute()

            action = "unfollowed"
        else:
            # Follow
            follow_data = {
                "follower_id": req.follower_id,
                "following_id": req.following_id,
                "created_at": datetime.now().isoformat()
            }

            supabase.table("user_follows").insert(follow_data).execute()
            action = "followed"

        return {
            "success": True,
            "action": action,
            "message": f"User {action} successfully!"
        }

    except Exception as e:
        print(f"❌ Error following user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to follow user: {str(e)}")


@router.get("/user-profile/{profile_user_id}")
def get_user_profile(profile_user_id: str, current_user_id: str = Query(...)):
    """Get user profile with community stats"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Get user basic info
        user_result = supabase.table("users") \
            .select("*") \
            .eq("id", profile_user_id) \
            .execute()

        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_result.data[0]

        # Get community stats
        shared_recipes_count = supabase.table("shared_recipes") \
            .select("id", count="exact") \
            .eq("user_id", profile_user_id) \
            .execute()

        followers_count = supabase.table("user_follows") \
            .select("id", count="exact") \
            .eq("following_id", profile_user_id) \
            .execute()

        following_count = supabase.table("user_follows") \
            .select("id", count="exact") \
            .eq("follower_id", profile_user_id) \
            .execute()

        # Check if current user is following this profile
        is_following_result = supabase.table("user_follows") \
            .select("id") \
            .eq("follower_id", current_user_id) \
            .eq("following_id", profile_user_id) \
            .execute()

        is_following = len(is_following_result.data or []) > 0

        # Check if profile user is following current user back
        is_followed_by_result = supabase.table("user_follows") \
            .select("id") \
            .eq("follower_id", profile_user_id) \
            .eq("following_id", current_user_id) \
            .execute()

        is_followed_by = len(is_followed_by_result.data or []) > 0

        profile = {
            "user_id": user_data["id"],
            "username": user_data.get("username", "Anonymous"),
            "display_name": user_data.get("display_name", "Community Chef"),
            "bio": user_data.get("bio", ""),
            "profile_image_url": user_data.get("profile_image_url"),
            "recipes_shared": shared_recipes_count.count if hasattr(shared_recipes_count, 'count') else 0,
            "followers_count": followers_count.count if hasattr(followers_count, 'count') else 0,
            "following_count": following_count.count if hasattr(following_count, 'count') else 0,
            "total_likes_received": 0,  # Would need additional calculation
            "is_following": is_following,
            "is_followed_by": is_followed_by,
            "favorite_cuisines": user_data.get("favorite_cuisines", []),
            "dietary_preferences": user_data.get("dietary_preferences", []),
            "member_since": user_data.get("created_at", "")
        }

        return profile

    except Exception as e:
        print(f"❌ Error getting user profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user profile: {str(e)}")


@router.get("/search-recipes")
def search_community_recipes(req: CommunitySearchRequest = Depends()):
    """Search shared recipes in the community"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        offset = (req.page - 1) * req.per_page

        # Build query based on search criteria
        query = supabase.table("shared_recipes") \
            .select("""
                *,
                users!inner(id, username, display_name, profile_image_url)
            """) \
            .eq("sharing_level", "public") \
            .limit(req.per_page) \
            .offset(offset)

        # Add search filters
        if req.cuisine:
            # This would need to search within the recipe_data JSON
            pass  # Implement JSON search

        # Apply sorting
        if req.sort_by == "recent":
            query = query.order("created_at", desc=True)
        elif req.sort_by == "popular":
            query = query.order("likes_count", desc=True)
        elif req.sort_by == "top_rated":
            # Would need rating calculation
            query = query.order("created_at", desc=True)

        result = query.execute()

        # Process results similar to community feed
        search_results = []
        for recipe in (result.data or []):
            search_results.append({
                "id": recipe["id"],
                "recipe_name": recipe["recipe_data"].get("recipe_name", "Shared Recipe"),
                "shared_by": {
                    "user_id": recipe["users"]["id"],
                    "username": recipe["users"].get("username", "Anonymous"),
                    "display_name": recipe["users"].get("display_name", "Community Chef")
                },
                "recipe_data": recipe["recipe_data"],
                "likes_count": recipe["likes_count"],
                "comments_count": recipe["comments_count"],
                "created_at": recipe["created_at"],
                "tags": recipe.get("tags", [])
            })

        return {
            "results": search_results,
            "total_count": len(search_results),
            "page": req.page,
            "has_more": len(search_results) == req.per_page
        }

    except Exception as e:
        print(f"❌ Error searching recipes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search recipes: {str(e)}")


@router.post("/save-recipe")
def save_shared_recipe(shared_recipe_id: str, user_id: str):
    """Save a shared recipe to user's collection"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Get the shared recipe data
        recipe_result = supabase.table("shared_recipes") \
            .select("*") \
            .eq("id", shared_recipe_id) \
            .execute()

        if not recipe_result.data:
            raise HTTPException(status_code=404, detail="Shared recipe not found")

        shared_recipe = recipe_result.data[0]

        # Save to user's favorites/collection
        save_data = {
            "user_id": user_id,
            "recipe_name": shared_recipe["recipe_data"].get("recipe_name", "Saved Recipe"),
            "recipe_data": shared_recipe["recipe_data"],
            "source": "community",
            "source_id": shared_recipe_id,
            "original_author_id": shared_recipe["user_id"],
            "added_at": datetime.now().isoformat()
        }

        insert_result = supabase.table("collection_favorites").insert(save_data).execute()

        if insert_result.data:
            # Track the save interaction
            interaction_data = {
                "user_id": user_id,
                "shared_recipe_id": shared_recipe_id,
                "action": "saved",
                "created_at": datetime.now().isoformat()
            }

            supabase.table("user_recipe_interactions").insert(interaction_data).execute()

            # Increment saves count
            supabase.rpc("increment_saves_count", {"recipe_id": shared_recipe_id}).execute()

            return {
                "success": True,
                "message": "Recipe saved to your collection!",
                "saved_id": insert_result.data[0]["id"]
            }

    except Exception as e:
        print(f"❌ Error saving recipe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save recipe: {str(e)}")


@router.get("/my-shared-recipes/{user_id}")
def get_my_shared_recipes(user_id: str):
    """Get recipes shared by the current user"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        my_recipes = supabase.table("shared_recipes") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .execute()

        recipes = []
        for recipe in (my_recipes.data or []):
            recipes.append({
                "id": recipe["id"],
                "recipe_name": recipe["recipe_data"].get("recipe_name", "My Recipe"),
                "recipe_data": recipe["recipe_data"],
                "sharing_level": recipe["sharing_level"],
                "created_at": recipe["created_at"],
                "likes_count": recipe["likes_count"],
                "comments_count": recipe["comments_count"],
                "views_count": recipe.get("views_count", 0),
                "saves_count": recipe.get("saves_count", 0),
                "message": recipe.get("message"),
                "tags": recipe.get("tags", [])
            })

        return {
            "shared_recipes": recipes,
            "total_count": len(recipes)
        }

    except Exception as e:
        print(f"❌ Error getting my shared recipes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get shared recipes: {str(e)}")