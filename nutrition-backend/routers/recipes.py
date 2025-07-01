# Updated routers/recipes.py with Supabase integration
import os
import json
import re
from fractions import Fraction
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from models.recipeModels import RecipeRequest, SingleRecipeRequest
from datetime import datetime
from dotenv import load_dotenv
from database import supabase

# Load environment variables FIRST
load_dotenv()

# NOW import and initialize OpenAI client
from openai import OpenAI

# Initialize router
router = APIRouter()

# Initialize OpenAI client with proper error handling
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("WARNING: OPENAI_API_KEY not found in environment variables")
    client = None
else:
    client = OpenAI(api_key=openai_api_key)

# Load ingredient prices with error handling
ingredient_prices = {}
try:
    with open("/Users/sravankundurthi/NutritionApp/nutrition-backend/Data/ingredient_prices.json") as f:
        ingredient_prices = json.load(f)
    print(f"Loaded {len(ingredient_prices)} ingredient prices")
except FileNotFoundError:
    print("Warning: ingredient_prices.json not found, using default prices")
    ingredient_prices = {}

# Helper functions
def estimate_grocery_list(ingredients: list):
    fallback_price = 1.00
    grocery_list = []
    for item in ingredients:
        name = item.get("name", "").lower()
        quantity = item.get("quantity", 1)
        unit_price = ingredient_prices.get(name, fallback_price)
        estimated_cost = round(unit_price * quantity, 2)
        grocery_list.append({
            "item": name,
            "quantity": quantity,
            "estimated_cost": estimated_cost
        })
    return grocery_list

def get_user_preferences(user_id: str):
    """Get user preferences from Supabase"""
    if not supabase:
        print("Supabase not available, using defaults")
        return {"budget": 20.0, "allergies": "", "diet": ""}
    
    try:
        pref_resp = supabase.table("user_preferences") \
            .select("budget, allergies, diet") \
            .eq("user_id", user_id) \
            .limit(1) \
            .execute()

        if pref_resp.data and len(pref_resp.data) > 0:
            prefs = pref_resp.data[0]
            try:
                user_budget = float(prefs.get("budget") or 20.0)
            except:
                user_budget = 20.0
            
            result = {
                'budget': user_budget,
                'allergies': prefs.get("allergies") or "",
                'diet': prefs.get("diet") or ""
            }
            print(f"Loaded user preferences: budget=${result['budget']}, allergies='{result['allergies']}', diet='{result['diet']}'")
            return result
        else:
            print("No user preferences found, using defaults")
            return {'budget': 20.0, 'allergies': "", 'diet': ""}
            
    except Exception as e:
        print(f"Error loading user preferences: {e}")
        return {'budget': 20.0, 'allergies': "", 'diet': ""}

def save_recipe_to_database(user_id: str, recipe_data: dict):
    """Save recipe to Supabase database"""
    if not supabase:
        print("Supabase not available, skipping recipe save")
        return None
        
    try:
        insert_result = supabase.table("recipes").insert({
            "user_id": user_id,
            "title": recipe_data["recipe_name"],
            "ingredients": recipe_data["ingredients"],
            "directions": recipe_data["directions"],
            "tags": recipe_data["tags"],
            "cuisine": recipe_data["cuisine"],
            "diet": recipe_data["diet"],
            "macro_estimate": recipe_data["macros"],
            "cost_estimate": recipe_data["cost_estimate"]
        }).execute()

        if insert_result.data and len(insert_result.data) > 0:
            recipe_id = insert_result.data[0]["id"]
            print(f"✅ Saved recipe '{recipe_data['recipe_name']}' to database with ID: {recipe_id}")
            return recipe_id
        else:
            print("⚠️ Recipe insert returned no data")
            return None
            
    except Exception as e:
        print(f"❌ Error saving recipe to database: {e}")
        return None

@router.post("/generate-recipe-with-grocery")
def generate_recipe_with_grocery(req: RecipeRequest):
    """Generate 3 recipes with grocery lists - used by GenerateRecipe.jsx"""
    try:
        # Check if OpenAI client is available
        if not client:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")

        # 1) Fetch user preferences from Supabase
        user_prefs = get_user_preferences(req.user_id)
        user_budget = user_prefs['budget'] if user_prefs['budget'] > 0 else req.budget
        user_allergies = user_prefs['allergies']
        user_diet = user_prefs['diet']
        
        print(f"Generating recipes for: {req.title}")
        print(f"Using budget: ${user_budget} (requested: ${req.budget})")
        print(f"User allergies: {user_allergies or 'None'}")
        print(f"User diet: {user_diet or 'None'}")

        prompt = f"""
        You are a world class chef that understands flavor, texture, and different cuisines who is exceptional at curating
        Recipes with budget, calories, different cuisines, and macro nutrients.
        
        Generate exactly THREE distinct recipes for: "{req.title}".

        Constraints:
        - Budget: ${user_budget:.2f} per recipe
        - Allergies: {user_allergies if user_allergies else 'None'}
        - Diet: {user_diet if user_diet else 'None'}

        Format each recipe EXACTLY like this:

        RECIPE 1: [Recipe Name]

        Ingredients:
        - 1 cup ingredient1
        - 2 tbsp ingredient2
        - 3 pieces ingredient3

        Directions:
        1. First step
        2. Second step
        3. Third step

        Nutrition Facts:
        - Calories: 450
        - Protein: 25g
        - Carbs: 35g
        - Fat: 15g
        - Fiber: 5g

        Tags: tag1, tag2, tag3
        Cuisine: Italian
        Diet: Balanced
        Cost Estimate: $8.50

        ---

        RECIPE 2: [Recipe Name]
        [Same format as above]

        ---

        RECIPE 3: [Recipe Name]
        [Same format as above]

        Make sure each recipe is complete with all sections.
        """.strip()

        # 2) Call OpenAI
        print("Calling OpenAI API...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        content = response.choices[0].message.content

        print("✅ Received OpenAI response")

        # 3) Parse the response (your existing parsing logic)
        raw_recipes = [blk.strip() for blk in content.split("---") if blk.strip()]

        if len(raw_recipes) < 3:
            raw_recipes = re.split(r'(?=RECIPE\s*\d+:)', content)
            raw_recipes = [blk.strip() for blk in raw_recipes if blk.strip()]

        raw_recipes = [r for r in raw_recipes if len(r) > 50]
        print(f"Found {len(raw_recipes)} recipe blocks")

        parsed_recipes = []
        for idx, recipe_text in enumerate(raw_recipes[:3]):
            print(f"Parsing recipe {idx + 1}...")

            # Extract recipe name
            recipe_name_match = re.search(r'RECIPE\s*\d+:\s*(.+)', recipe_text)
            recipe_name = recipe_name_match.group(1).strip() if recipe_name_match else f"Recipe {idx + 1}"

            # Parse ingredients
            parsed_ingredients = []
            ingredients_match = re.search(r'Ingredients:\s*\n(.*?)(?=\n\s*Directions:|\n\s*Nutrition|\Z)', recipe_text,
                                          re.DOTALL | re.IGNORECASE)

            if ingredients_match:
                ingredients_text = ingredients_match.group(1)
                for line in ingredients_text.strip().split('\n'):
                    line = line.strip()
                    if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                        line = re.sub(r'^[-•*]\s*', '', line).strip()
                        parts = line.split(' ', 2)
                        
                        if len(parts) >= 2:
                            try:
                                quantity_str = parts[0]
                                quantity = float(Fraction(quantity_str))
                                if len(parts) == 3:
                                    unit, name = parts[1], parts[2]
                                else:
                                    unit, name = "", parts[1]
                            except:
                                quantity = 1.0
                                unit, name = parts[0], ' '.join(parts[1:])
                        else:
                            quantity, unit, name = 1.0, "", line

                        parsed_ingredients.append({
                            "name": name.strip().lower(),
                            "unit": unit.strip(),
                            "quantity": quantity
                        })

            # Parse directions
            parsed_directions = []
            directions_match = re.search(r'Directions:\s*\n(.*?)(?=\n\s*Nutrition|\n\s*Tags:|\Z)', recipe_text,
                                         re.DOTALL | re.IGNORECASE)

            if directions_match:
                directions_text = directions_match.group(1)
                for line in directions_text.strip().split('\n'):
                    line = line.strip()
                    if line and (re.match(r'^\d+\.', line) or line.startswith('-')):
                        line = re.sub(r'^\d+\.\s*', '', line)
                        line = re.sub(r'^[-•*]\s*', '', line)
                        if line.strip():
                            parsed_directions.append(line.strip())

            # Parse nutrition macros
            macros = {"calories": 0.0, "protein": "0g", "carbs": "0g", "fat": "0g", "fiber": "0g"}
            nutrition_match = re.search(r'Nutrition Facts:\s*\n(.*?)(?=\n\s*Tags:|\n\s*Cuisine:|\Z)', recipe_text,
                                        re.DOTALL | re.IGNORECASE)

            if nutrition_match:
                nutrition_text = nutrition_match.group(1)
                for line in nutrition_text.strip().split('\n'):
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().lower().replace('-', '').replace('•', '').replace('*', '').strip()
                        value = value.strip()

                        if key == 'calories':
                            try:
                                macros['calories'] = float(re.search(r'([\d.]+)', value).group(1))
                            except:
                                macros['calories'] = 0.0
                        elif key in ['protein', 'carbs', 'fat', 'fiber']:
                            macros[key] = value

            # Parse tags, cuisine, diet
            tags = []
            tag_match = re.search(r'Tags:\s*(.+)', recipe_text, re.IGNORECASE)
            if tag_match:
                raw_tags = tag_match.group(1)
                tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]

            cuisine = "Unknown"
            diet = "Unknown"
            cuisine_match = re.search(r'Cuisine:\s*(.+)', recipe_text, re.IGNORECASE)
            if cuisine_match:
                cuisine = cuisine_match.group(1).strip()
            diet_match = re.search(r'Diet:\s*(.+)', recipe_text, re.IGNORECASE)
            if diet_match:
                diet = diet_match.group(1).strip()

            # Parse cost estimate
            cost_estimate = 0.0
            cost_match = re.search(r'Cost Estimate:\s*\$?([\d.]+)', recipe_text)
            if cost_match:
                cost_estimate = float(cost_match.group(1))
            else:
                cost_estimate = round(
                    sum(ingredient_prices.get(i["name"], 1.00) * i["quantity"]
                        for i in parsed_ingredients),
                    2
                )

            # Build grocery list
            grocery_list = estimate_grocery_list(parsed_ingredients)

            recipe_data = {
                "recipe_text": recipe_text,
                "recipe_name": recipe_name,
                "ingredients": parsed_ingredients,
                "directions": parsed_directions,
                "macros": macros,
                "tags": tags,
                "cuisine": cuisine,
                "diet": diet,
                "cost_estimate": round(cost_estimate, 2),
                "grocery_list": grocery_list
            }

            # 4) Save recipe to database
            recipe_id = save_recipe_to_database(req.user_id, recipe_data)
            if recipe_id:
                recipe_data["recipe_id"] = recipe_id

            parsed_recipes.append(recipe_data)
            print(f"✅ Completed recipe {idx + 1}: {recipe_name}")

        print(f"🎉 Successfully generated and saved {len(parsed_recipes)} recipes")
        return {"recipes": parsed_recipes}

    except Exception as e:
        print(f"❌ Error in generate_recipe_with_grocery: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recipes: {str(e)}")


@router.post("/generate-single-recipe")
def generate_single_recipe(req: SingleRecipeRequest):
    """Regenerate a single recipe - used by GenerateRecipe.jsx"""
    try:
        if not client:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")

        # Get user preferences
        user_prefs = get_user_preferences(req.user_id)
        user_budget = user_prefs['budget'] if user_prefs['budget'] > 0 else req.budget
        user_allergies = user_prefs['allergies']
        user_diet = user_prefs['diet']

        print(f"Regenerating single recipe for: {req.title}")

        # Build exclusion context
        exclusion_context = ""
        if req.exclude_recipes:
            recipe_names = []
            for recipe in req.exclude_recipes:
                if recipe.get("recipe_name"):
                    recipe_names.append(recipe["recipe_name"])
                elif recipe.get("recipe_text"):
                    first_line = recipe["recipe_text"].split('\n')[0]
                    recipe_names.append(first_line)

            if recipe_names:
                exclusion_context = f"\n\nIMPORTANT: Do NOT generate any recipe similar to these existing ones: {', '.join(recipe_names)}. Create something completely different."

        prompt = f"""
        Generate exactly ONE unique recipe for: "{req.title}".

        Constraints:
        - Budget: ${user_budget:.2f}
        - Allergies: {user_allergies if user_allergies else 'None'}
        - Diet: {user_diet if user_diet else 'None'}
        {exclusion_context}

        Format the recipe EXACTLY like this:

        RECIPE: [Unique Recipe Name]

        Ingredients:
        - 1 cup ingredient1
        - 2 tbsp ingredient2

        Directions:
        1. First step
        2. Second step

        Nutrition Facts:
        - Calories: 450
        - Protein: 25g
        - Carbs: 35g
        - Fat: 15g
        - Fiber: 5g

        Tags: tag1, tag2
        Cuisine: Italian
        Diet: Balanced
        Cost Estimate: $8.50

        Make the recipe completely unique and different from any existing ones.
        """.strip()

        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        recipe_text = response.choices[0].message.content.strip()

        # Simplified parsing for single recipe
        recipe_name_match = re.search(r'RECIPE:\s*(.+)', recipe_text)
        recipe_name = recipe_name_match.group(1).strip() if recipe_name_match else "New Recipe"

        # Use basic parsing
        parsed_ingredients = []
        parsed_directions = []
        macros = {"calories": 400, "protein": "20g", "carbs": "30g", "fat": "15g", "fiber": "5g"}
        
        # Simple ingredient parsing
        if "Ingredients:" in recipe_text:
            ing_section = recipe_text.split("Ingredients:")[1].split("Directions:")[0]
            for line in ing_section.split('\n'):
                line = line.strip()
                if line.startswith('-'):
                    ingredient_name = line[1:].strip()
                    parsed_ingredients.append({
                        "name": ingredient_name.lower(),
                        "unit": "",
                        "quantity": 1.0
                    })

        grocery_list = estimate_grocery_list(parsed_ingredients)

        recipe_data = {
            "recipe_text": recipe_text,
            "recipe_name": recipe_name,
            "ingredients": parsed_ingredients,
            "directions": ["Follow the recipe instructions"],  # Simplified
            "macros": macros,
            "tags": ["quick"],
            "cuisine": "Modern",
            "diet": "Balanced",
            "cost_estimate": round(user_budget, 2),
            "grocery_list": grocery_list
        }

        # Save to database
        recipe_id = save_recipe_to_database(req.user_id, recipe_data)
        if recipe_id:
            recipe_data["recipe_id"] = recipe_id

        print(f"✅ Generated single recipe: {recipe_name}")
        return {"recipe": recipe_data}

    except Exception as e:
        print(f"❌ Error in generate_single_recipe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recipe: {str(e)}")


@router.get("/search-recipes")
def search_recipes(
    user_id: str = Query(...),
    keyword: Optional[str] = Query(None),
    max_cost: Optional[float] = Query(None),
    tag: Optional[str] = Query(None),
    cuisine: Optional[str] = Query(None),
    diet: Optional[str] = Query(None),
):
    """Search user's recipes - used by search functionality"""
    try:
        if not supabase:
            return {"results": [], "count": 0}
            
        # Build base query
        query = supabase.table("recipes").select("*").eq("user_id", user_id)
        
        # Add filters
        if max_cost is not None:
            query = query.lte("cost_estimate", max_cost)
            
        # Execute query
        result = query.execute()
        recipes = result.data or []
        
        # Apply keyword search (simplified)
        if keyword:
            keyword_lower = keyword.lower()
            recipes = [r for r in recipes if keyword_lower in r.get("title", "").lower()]
            
        print(f"Found {len(recipes)} recipes for user {user_id}")
        
        return {
            "results": recipes,
            "count": len(recipes)
        }
        
    except Exception as e:
        print(f"Error in search_recipes: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")