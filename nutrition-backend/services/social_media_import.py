import os
import re
import json
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class SocialMediaImportService:
    """Service for importing recipes from social media platforms"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
            print("⚠️ OpenAI API key not found - AI features disabled")

        # Platform patterns
        self.platform_patterns = {
            'tiktok': r'(?:www\.)?tiktok\.com/@[\w.-]+/video/\d+',
            'instagram': r'(?:www\.)?instagram\.com/(?:p|reel)/[\w-]+',
            'youtube': r'(?:www\.)?youtube\.com/(?:watch\?v=|shorts/)[\w-]+',
            'pinterest': r'(?:www\.)?pinterest\.com/pin/\d+'
        }

    def detect_platform(self, url: str) -> Optional[str]:
        """Detect which platform the URL is from"""
        for platform, pattern in self.platform_patterns.items():
            if re.search(pattern, url, re.IGNORECASE):
                return platform
        return None

    async def extract_recipe_from_url(self, url: str, platform: str, user_id: str) -> Optional[Dict]:
        """Extract recipe from social media URL"""
        try:
            # For demo purposes, we'll simulate extraction
            # In production, you'd use platform APIs or web scraping

            print(f"🔍 Extracting recipe from {platform} URL: {url}")

            # Simulate API call to platform
            # In reality, you'd need to:
            # 1. Use platform APIs (if available)
            # 2. Web scrape the content
            # 3. Extract video captions/descriptions

            # For now, we'll use AI to generate a plausible recipe based on the platform
            if not self.client:
                return self._get_demo_recipe(platform)

            prompt = f"""Based on this {platform} URL: {url}

Generate a realistic recipe that might be found on {platform}. The recipe should be:
- Trendy and visually appealing (typical of {platform} food content)
- Include popular ingredients and techniques
- Have clear, simple instructions
- Include prep/cook times and difficulty level

Return ONLY valid JSON with this structure:
{{
    "recipe_name": "Recipe Title",
    "description": "Brief description",
    "ingredients": ["ingredient 1", "ingredient 2", ...],
    "directions": ["step 1", "step 2", ...],
    "prep_time": "X minutes",
    "cook_time": "Y minutes",
    "servings": Z,
    "difficulty": "easy/medium/hard",
    "tags": ["tag1", "tag2", ...],
    "cuisine": "cuisine type",
    "diet": "dietary info",
    "cost_estimate": "$X.XX",
    "macros": {{
        "calories": X,
        "protein": "Xg",
        "carbs": "Xg",
        "fat": "Xg",
        "fiber": "Xg"
    }},
    "social_metrics": {{
        "platform": "{platform}",
        "trending": true,
        "viral_score": 0.85
    }}
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a social media recipe extraction expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            recipe_json = response.choices[0].message.content.strip()
            recipe_data = json.loads(recipe_json)

            # Add metadata
            recipe_data["imported_from"] = platform
            recipe_data["source_url"] = url
            recipe_data["imported_at"] = datetime.now().isoformat()

            return recipe_data

        except Exception as e:
            print(f"❌ Error extracting from URL: {str(e)}")
            return self._get_demo_recipe(platform)

    async def extract_recipe_from_image(self, image_base64: str, user_id: str) -> Optional[Dict]:
        """Extract recipe from food image using AI vision"""
        try:
            if not self.client:
                return self._get_demo_recipe("image")

            # Use GPT-4 Vision to analyze the image
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a culinary expert who can identify dishes and create recipes from food images."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Analyze this food image and create a detailed recipe.

Identify:
1. The dish name and cuisine type
2. Visible ingredients
3. Cooking method used
4. Estimated prep and cook time
5. Difficulty level

Return ONLY valid JSON with this structure:
{
    "recipe_name": "Identified Dish Name",
    "description": "Brief description of the dish",
    "ingredients": ["ingredient 1 with amount", "ingredient 2 with amount", ...],
    "directions": ["detailed step 1", "detailed step 2", ...],
    "prep_time": "X minutes",
    "cook_time": "Y minutes",
    "servings": Z,
    "difficulty": "easy/medium/hard",
    "tags": ["tag1", "tag2", ...],
    "cuisine": "cuisine type",
    "diet": "dietary info if apparent",
    "cost_estimate": "$X.XX",
    "macros": {
        "calories": X,
        "protein": "Xg",
        "carbs": "Xg",
        "fat": "Xg",
        "fiber": "Xg"
    },
    "extraction_confidence": 0.0-1.0,
    "identified_elements": ["visible element 1", "visible element 2", ...]
}"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )

            recipe_json = response.choices[0].message.content.strip()
            recipe_data = json.loads(recipe_json)

            # Add metadata
            recipe_data["source"] = "image_recognition"
            recipe_data["extracted_at"] = datetime.now().isoformat()

            return recipe_data

        except Exception as e:
            print(f"❌ Error extracting from image: {str(e)}")
            return self._get_demo_recipe("image")

    async def create_alternative_recipe(
            self,
            original_recipe: Dict,
            alternative_type: str,
            user_id: str,
            preserve_flavors: bool = True
    ) -> Optional[Dict]:
        """Create an alternative version of a recipe"""
        try:
            if not self.client:
                return self._get_demo_alternative(original_recipe, alternative_type)

            # Build the prompt based on alternative type
            constraints = self._get_alternative_constraints(alternative_type)

            prompt = f"""Transform this recipe into a {alternative_type} version:

Original Recipe:
{json.dumps(original_recipe, indent=2)}

Requirements:
{constraints}

Additional instructions:
- Preserve flavors: {preserve_flavors}
- Maintain the essence and appeal of the original dish
- Suggest smart substitutions
- Keep instructions clear and simple
- Calculate accurate nutritional information

Return ONLY valid JSON with the same structure as the original recipe, but with all modifications applied."""

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a culinary expert specializing in recipe adaptations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            alternative_json = response.choices[0].message.content.strip()
            alternative_data = json.loads(alternative_json)

            # Add metadata
            alternative_data["alternative_type"] = alternative_type
            alternative_data["based_on"] = original_recipe.get("recipe_name", "Original Recipe")
            alternative_data["modifications"] = self._calculate_modifications(original_recipe, alternative_data)

            return alternative_data

        except Exception as e:
            print(f"❌ Error creating alternative: {str(e)}")
            return self._get_demo_alternative(original_recipe, alternative_type)

    def _get_alternative_constraints(self, alternative_type: str) -> str:
        """Get constraints for different alternative types"""
        constraints_map = {
            "healthier": """
- Reduce calories by 20-30%
- Increase protein and fiber
- Reduce saturated fat and sugar
- Use whole grains instead of refined
- Include more vegetables
- Use healthier cooking methods (baking vs frying)
- Maintain satisfying portions""",

            "budget": """
- Reduce cost by at least 40%
- Use affordable protein sources
- Substitute expensive ingredients with budget alternatives
- Buy seasonal produce
- Use pantry staples
- Maintain nutritional value
- Keep it filling and satisfying""",

            "quick": """
- Total time under 30 minutes
- Minimize prep work
- Use pre-cut or frozen vegetables
- One-pot or sheet pan methods preferred
- Use time-saving appliances
- Reduce number of steps
- Keep ingredients list simple""",

            "vegan": """
- Remove all animal products
- Replace with plant-based alternatives
- Ensure adequate protein
- Add umami flavors
- Use nutritional yeast, nuts, or seeds
- Maintain creamy textures with plant milk/cashews
- Keep it satisfying and flavorful""",

            "keto": """
- Keep net carbs under 10g per serving
- High fat content (70%+ calories)
- Moderate protein
- Replace grains and sugars
- Use low-carb vegetables
- Include healthy fats
- Maintain satiety"""
        }

        return constraints_map.get(alternative_type, "Create a modified version that's appealing and practical")

    def _calculate_modifications(self, original: Dict, alternative: Dict) -> Dict:
        """Calculate what changed between recipes"""
        modifications = {
            "ingredients_changed": 0,
            "cost_difference": "",
            "calorie_difference": "",
            "time_difference": "",
            "key_substitutions": []
        }

        try:
            # Compare ingredients
            original_ingredients = set(original.get("ingredients", []))
            alt_ingredients = set(alternative.get("ingredients", []))
            modifications["ingredients_changed"] = len(original_ingredients.symmetric_difference(alt_ingredients))

            # Cost comparison
            orig_cost = float(original.get("cost_estimate", "0").replace("$", ""))
            alt_cost = float(alternative.get("cost_estimate", "0").replace("$", ""))
            cost_diff = alt_cost - orig_cost
            modifications["cost_difference"] = f"${cost_diff:+.2f}"

            # Calorie comparison
            orig_cal = original.get("macros", {}).get("calories", 0)
            alt_cal = alternative.get("macros", {}).get("calories", 0)
            cal_diff = alt_cal - orig_cal
            modifications["calorie_difference"] = f"{cal_diff:+d} calories"

        except Exception as e:
            print(f"Error calculating modifications: {e}")

        return modifications

    def _get_demo_recipe(self, source: str) -> Dict:
        """Return a demo recipe when AI is not available"""
        demos = {
            "tiktok": {
                "recipe_name": "Viral Baked Feta Pasta",
                "description": "The TikTok-famous pasta dish that broke the internet",
                "ingredients": [
                    "1 block (7 oz) feta cheese",
                    "2 cups cherry tomatoes",
                    "1/2 cup olive oil",
                    "4 cloves garlic, minced",
                    "1 lb pasta",
                    "1/4 cup fresh basil",
                    "Salt and pepper to taste"
                ],
                "directions": [
                    "Preheat oven to 400°F",
                    "Place feta and tomatoes in a baking dish",
                    "Drizzle with olive oil, add garlic, salt, and pepper",
                    "Bake for 35 minutes until tomatoes burst",
                    "Cook pasta according to package",
                    "Mix everything together with basil"
                ],
                "prep_time": "5 minutes",
                "cook_time": "35 minutes",
                "servings": 4,
                "difficulty": "easy",
                "tags": ["viral", "pasta", "vegetarian", "tiktok"],
                "cuisine": "Mediterranean",
                "diet": "Vegetarian",
                "cost_estimate": "$12.50",
                "macros": {
                    "calories": 485,
                    "protein": "14g",
                    "carbs": "52g",
                    "fat": "26g",
                    "fiber": "3g"
                }
            },
            "instagram": {
                "recipe_name": "Cloud Bread Pizza",
                "description": "Low-carb pizza using the Instagram-famous cloud bread",
                "ingredients": [
                    "3 large eggs, separated",
                    "3 tbsp cream cheese, softened",
                    "1/4 tsp baking powder",
                    "1/2 cup pizza sauce",
                    "1 cup mozzarella cheese",
                    "Favorite pizza toppings"
                ],
                "directions": [
                    "Whip egg whites until stiff peaks form",
                    "Mix yolks with cream cheese and baking powder",
                    "Fold whites into yolk mixture gently",
                    "Spread on parchment-lined baking sheet",
                    "Bake at 300°F for 25 minutes",
                    "Add toppings and bake 5 more minutes"
                ],
                "prep_time": "15 minutes",
                "cook_time": "30 minutes",
                "servings": 2,
                "difficulty": "medium",
                "tags": ["keto", "low-carb", "pizza", "trending"],
                "cuisine": "Italian-American",
                "diet": "Keto",
                "cost_estimate": "$8.75",
                "macros": {
                    "calories": 285,
                    "protein": "18g",
                    "carbs": "5g",
                    "fat": "22g",
                    "fiber": "1g"
                }
            },
            "image": {
                "recipe_name": "Honey Garlic Chicken Stir-Fry",
                "description": "Quick and flavorful chicken stir-fry with vegetables",
                "ingredients": [
                    "1 lb chicken breast, cubed",
                    "2 tbsp honey",
                    "3 cloves garlic, minced",
                    "2 tbsp soy sauce",
                    "1 bell pepper, sliced",
                    "1 cup broccoli florets",
                    "2 tbsp vegetable oil",
                    "1 tsp cornstarch"
                ],
                "directions": [
                    "Mix honey, garlic, and soy sauce",
                    "Heat oil in a wok or large pan",
                    "Cook chicken until golden",
                    "Add vegetables and stir-fry for 3 minutes",
                    "Pour sauce over and toss",
                    "Thicken with cornstarch slurry if needed"
                ],
                "prep_time": "10 minutes",
                "cook_time": "15 minutes",
                "servings": 4,
                "difficulty": "easy",
                "tags": ["quick", "stir-fry", "asian", "healthy"],
                "cuisine": "Asian Fusion",
                "diet": "High Protein",
                "cost_estimate": "$14.25",
                "macros": {
                    "calories": 325,
                    "protein": "28g",
                    "carbs": "18g",
                    "fat": "14g",
                    "fiber": "3g"
                },
                "extraction_confidence": 0.92
            }
        }

        return demos.get(source, demos["image"])

    def _get_demo_alternative(self, original: Dict, alternative_type: str) -> Dict:
        """Return a demo alternative recipe"""
        base_name = original.get("recipe_name", "Recipe")

        alternatives = {
            "healthier": {
                "recipe_name": f"Healthy {base_name}",
                "description": "A lighter, more nutritious version",
                "cost_estimate": "$11.50",
                "macros": {
                    "calories": 285,
                    "protein": "22g",
                    "carbs": "32g",
                    "fat": "8g",
                    "fiber": "6g"
                }
            },
            "budget": {
                "recipe_name": f"Budget-Friendly {base_name}",
                "description": "Same great taste, half the cost",
                "cost_estimate": "$6.75",
                "macros": {
                    "calories": 380,
                    "protein": "18g",
                    "carbs": "45g",
                    "fat": "14g",
                    "fiber": "4g"
                }
            },
            "quick": {
                "recipe_name": f"15-Minute {base_name}",
                "description": "Quick version for busy weeknights",
                "prep_time": "5 minutes",
                "cook_time": "10 minutes",
                "cost_estimate": "$10.25",
                "macros": {
                    "calories": 340,
                    "protein": "20g",
                    "carbs": "38g",
                    "fat": "12g",
                    "fiber": "3g"
                }
            }
        }

        # Get the alternative or use budget as default
        alt = alternatives.get(alternative_type, alternatives["budget"])

        # Merge with original recipe structure
        alternative_recipe = original.copy()
        alternative_recipe.update(alt)

        # Update some ingredients to show changes
        if "ingredients" in alternative_recipe:
            alternative_recipe["ingredients"] = [
                ing.replace("regular", "whole wheat").replace("white", "brown")
                for ing in alternative_recipe["ingredients"]
            ]

        return alternative_recipe