# nutrition-backend/models/communityModels.py

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ShareRecipeRequest(BaseModel):
    user_id: str
    recipe_id: Optional[str] = None
    recipe_data: Dict[str, Any]
    sharing_level: str = "public"  # public, friends, private
    message: Optional[str] = None
    tags: Optional[List[str]] = []

class RecipeCommentRequest(BaseModel):
    user_id: str
    shared_recipe_id: str
    comment_text: str
    parent_comment_id: Optional[str] = None  # For reply threading

class FollowUserRequest(BaseModel):
    follower_id: str
    following_id: str

class CommunitySearchRequest(BaseModel):
    user_id: str
    query: Optional[str] = ""
    cuisine: Optional[str] = None
    dietary_restrictions: Optional[List[str]] = []
    max_cost: Optional[float] = None
    max_cook_time: Optional[int] = None
    sort_by: str = "popular"  # popular, recent, top_rated
    page: int = 1
    per_page: int = 20

class CreateMealPlanGroupRequest(BaseModel):
    user_id: str
    name: str
    description: Optional[str] = None
    is_private: bool = False
    invited_users: Optional[List[str]] = []

class ShareMealPlanRequest(BaseModel):
    user_id: str
    group_id: str
    meal_plan_data: Dict[str, Any]
    week_starting: str  # YYYY-MM-DD format
    message: Optional[str] = None

class RateSharedRecipeRequest(BaseModel):
    user_id: str
    shared_recipe_id: str
    rating: int  # 1-5 stars
    review_text: Optional[str] = None

class RecipeTipRequest(BaseModel):
    user_id: str
    shared_recipe_id: str
    tip_type: str  # substitution, technique, cost_saving, time_saving
    tip_text: str
    ingredients_mentioned: Optional[List[str]] = []

# Response Models
class SharedRecipeResponse(BaseModel):
    id: str
    recipe_name: str
    shared_by: Dict[str, Any]  # User info
    recipe_data: Dict[str, Any]
    sharing_level: str
    created_at: str
    likes_count: int
    comments_count: int
    rating_average: float
    total_ratings: int
    is_liked_by_user: bool
    is_saved_by_user: bool
    tags: List[str]

class CommunityUserProfile(BaseModel):
    user_id: str
    username: str
    display_name: str
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    recipes_shared: int
    followers_count: int
    following_count: int
    total_likes_received: int
    is_following: bool
    is_followed_by: bool
    favorite_cuisines: List[str]
    dietary_preferences: List[str]
    member_since: str

class MealPlanGroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_by: Dict[str, Any]
    member_count: int
    is_private: bool
    shared_plans_count: int
    recent_activity: List[Dict[str, Any]]
    user_role: str  # owner, member, invited

class RecipeInteractionStats(BaseModel):
    shared_recipe_id: str
    total_views: int
    total_likes: int
    total_saves: int
    total_comments: int
    total_shares: int
    rating_distribution: Dict[str, int]  # {"5": 10, "4": 5, ...}
    most_common_tips: List[str]
    user_demographics: Dict[str, Any]