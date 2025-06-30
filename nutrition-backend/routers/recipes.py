from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from models.recipe_models import RecipeRequest, SingleRecipeRequest
from services.recipe_service import RecipeService
from services.openai_service import OpenAIService
from database import supabase

router = APIRouter()
recipe_service = RecipeService()
openai_service = OpenAIService()

@router.post("/generate-recipe-with-grocery")
async def generate_recipe_with_grocery(req: RecipeRequest):
    """Generate 3 recipes with grocery lists - used by GenerateRecipe.jsx"""
    try:
        return await recipe_service.generate_recipes_with_grocery(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recipes: {str(e)}")

@router.post("/generate-single-recipe")
async def generate_single_recipe(req: SingleRecipeRequest):
    """Regenerate a single recipe - used by GenerateRecipe.jsx"""
    try:
        return await recipe_service.generate_single_recipe(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recipe: {str(e)}")

@router.get("/search-recipes")
async def search_recipes(
    user_id: str = Query(...),
    keyword: Optional[str] = Query(None),
    max_cost: Optional[float] = Query(None),
    tag: Optional[str] = Query(None),
    cuisine: Optional[str] = Query(None),
    diet: Optional[str] = Query(None),
):
    """Search user's recipes - used by search functionality"""
    try:
        return await recipe_service.search_recipes(user_id, keyword, max_cost, tag, cuisine, diet)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")