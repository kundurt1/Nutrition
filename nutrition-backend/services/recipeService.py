import json
import re
from fractions import Fraction
from typing import List, Optional
from datetime import datetime

from models.recipe_models import RecipeRequest, SingleRecipeRequest
from services.openai_service import OpenAIService
from utils.ingredient_parser import IngredientParser
from utils.price_calculator import PriceCalculator
from database import supabase

class RecipeService:
    def __init__(self):
        self.openai_service = OpenAIService()
        self.ingredient_parser = IngredientParser()
        self.price_calculator = PriceCalculator()

    async def generate_recipes_with_grocery(self, req: RecipeRequest):
        """Generate 3 recipes with grocery lists"""
        # Get user preferences
        user_preferences = await self._get_user_preferences(req.user_id)
        
        # Generate recipes using OpenAI
        recipes_text = await self.openai_service.generate_three_recipes(
            req.title, 
            user_preferences['budget'], 
            user_preferences['allergies'], 
            user_preferences['diet']
        )
        
        # Parse recipes
        parsed_recipes = self._parse_recipes(recipes_text, req.user_id)
        
        return {"recipes": parsed_recipes}

    async def generate_single_recipe(self, req: SingleRecipeRequest):
        """Generate a single recipe for regeneration"""
        user_preferences = await self._get_user_preferences(req.user_id)
        
        # Build exclusion context
        exclusion_context = self._build_exclusion_context(req.exclude_recipes)
        
        # Generate single recipe
        recipe_text = await self.openai_service.generate_single_recipe(
            req.title,
            user_preferences['budget'],
            user_preferences['allergies'],
            user_preferences['diet'],
            exclusion_context
        )
        
        # Parse single recipe
        parsed_recipe = self._parse_single_recipe(recipe_text, req.user_id)
        
        return {"recipe": parsed_recipe}

    async def _get_user_preferences(self, user_id: str) -> dict:
        """Get user preferences from database"""
        pref_resp = supabase.table("user_preferences") \
            .select("budget, allergies, diet") \
            .eq("user_id", user_id) \
            .limit(1) \
            .execute()

        if pref_resp.data and len(pref_resp.data) > 0:
            prefs = pref_resp.data[0]
            return {
                'budget': float(prefs.get("budget", 20.0)) if prefs.get("budget") else 20.0,
                'allergies': prefs.get("allergies", ""),
                'diet': prefs.get("diet", "")
            }
        
        return {'budget': 20.0, 'allergies': "", 'diet': ""}

    def _parse_recipes(self, content: str, user_id: str) -> List[dict]:
        """Parse multiple recipes from OpenAI response"""
        # Implementation of your existing parsing logic
        # This would contain your current recipe parsing code
        pass

    def _parse_single_recipe(self, content: str, user_id: str) -> dict:
        """Parse single recipe from OpenAI response"""
        # Implementation of your existing single recipe parsing logic
        pass
