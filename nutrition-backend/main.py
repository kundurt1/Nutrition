import os
import json
import re
from fractions import Fraction
from fastapi.middleware.cors import CORSMiddleware

import openai
from openai import OpenAI
from dotenv import load_dotenv
from fastapi import FastAPI, Body, Query,HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
from datetime import datetime, timedelta,date

from typing import Optional, List, Dict
import uuid
from rapidfuzz import fuzz
from typing import Optional
from fastapi import Query
import uuid



# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# OpenAI setup
openai.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Load ingredient prices
with open("/Users/sravankundurthi/NutritionApp/nutrition-backend/Data/ingredient_prices.json") as f:
    ingredient_prices = json.load(f)

# ---------------- Models ----------------
class RecipeRequest(BaseModel):
    title: str
    budget: float
    user_id: str

class LogMealRequest(BaseModel):
    user_id: str
    recipe_id: str
    date: Optional[str] = None

class TrackMealRequest(BaseModel):
    user_id: str
    recipe: dict  # JSON structure of a recipe object

class CustomEntryRequest(BaseModel):
    user_id: str
    food_name: str
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: Optional[float] = 0.0
    date: Optional[str] = None  # YYYY-MM-DD format
class SingleRecipeRequest(BaseModel):
    title: str
    budget: float
    user_id: str
    regenerate_single: bool = True
    exclude_recipes: Optional[list] = []


class RateRecipeRequest(BaseModel):
    user_id: str
    recipe_id: Optional[str] = None  # Changed to str to handle UUID
    recipe_data: Optional[dict] = None  # For rating generated recipes not yet saved
    rating: int
    feedback_reason: Optional[str] = None

class UserPreferenceUpdate(BaseModel):
    user_id: str
    disliked_ingredients: List[str]
    disliked_cuisines: List[str]
    preferred_ingredients: List[str]
# New Pydantic models for favorites
class AddFavoriteRequest(BaseModel):
    user_id: str
    recipe_id: Optional[str] = None  # For saved recipes
    recipe_data: Optional[dict] = None  # For generated recipes
    recipe_name: str
    notes: Optional[str] = None

class RemoveFavoriteRequest(BaseModel):
    user_id: str
    favorite_id: str

class CreateCollectionRequest(BaseModel):
    user_id: str
    name: str
    description: Optional[str] = None

class AddToCollectionRequest(BaseModel):
    collection_id: str
    favorite_id: str

# Root check
@app.get("/")
def root():
    return {"api_key_loaded": bool(os.getenv("OPENAI_API_KEY"))}

# Generate recipe
def parse_macros_from_text(text: str):
    macros = {k: 0.0 for k in ["calories", "protein", "carbs", "fat", "fiber"]}
    for key in macros:
        match = re.search(fr"{key.capitalize()}: *([\d.]+)", text)
        if match:
            macros[key] = float(match.group(1))
    return macros

# Helper to estimate grocery list cost
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


@app.post("/generate-recipe-with-grocery")
def generate_recipe_with_grocery(req: RecipeRequest):
    try:
        # 1) Fetch user preferences - FIXED: Remove .single() and handle multiple rows
        pref_resp = supabase.table("user_preferences") \
            .select("budget, allergies, diet") \
            .eq("user_id", req.user_id) \
            .limit(1) \
            .execute()

        if pref_resp.data and len(pref_resp.data) > 0:
            prefs = pref_resp.data[0]  # Get the first row
            # Cast budget (text) to float if possible
            try:
                user_budget = float(prefs.get("budget") or req.budget)
            except:
                user_budget = req.budget
            user_allergies = prefs.get("allergies") or ""
            user_diet = prefs.get("diet") or ""
        else:
            # No preferences found, use defaults
            user_budget = req.budget
            user_allergies = ""
            user_diet = ""

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

        # 3) Call OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        content = response.choices[0].message.content

        print("Raw OpenAI Response:")
        print(content)
        print("=" * 50)

        # 4) IMPROVED parsing - split by "---" or "RECIPE X:"
        # First try splitting by ---
        raw_recipes = [blk.strip() for blk in content.split("---") if blk.strip()]

        # If that doesn't work, try splitting by RECIPE pattern
        if len(raw_recipes) < 3:
            raw_recipes = re.split(r'(?=RECIPE\s*\d+:)', content)
            raw_recipes = [blk.strip() for blk in raw_recipes if blk.strip()]

        # Remove any empty or very short blocks
        raw_recipes = [r for r in raw_recipes if len(r) > 50]

        print(f"Found {len(raw_recipes)} recipe blocks")
        for i, recipe in enumerate(raw_recipes):
            print(f"Recipe {i + 1} preview: {recipe[:100]}...")
        print("=" * 50)

        parsed_recipes = []
        for idx, recipe_text in enumerate(raw_recipes[:3]):  # Only take first 3
            print(f"Parsing recipe {idx + 1}:")
            print(recipe_text[:200] + "...")

            # Extract recipe name from "RECIPE X: Name" pattern
            recipe_name_match = re.search(r'RECIPE\s*\d+:\s*(.+)', recipe_text)
            recipe_name = recipe_name_match.group(1).strip() if recipe_name_match else f"Recipe {idx + 1}"

            # Parse ingredients - look for lines starting with - or •
            parsed_ingredients = []
            ingredients_match = re.search(r'Ingredients:\s*\n(.*?)(?=\n\s*Directions:|\n\s*Nutrition|\Z)', recipe_text,
                                          re.DOTALL | re.IGNORECASE)

            if ingredients_match:
                ingredients_text = ingredients_match.group(1)
                for line in ingredients_text.strip().split('\n'):
                    line = line.strip()
                    if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                        # Remove bullet point and parse
                        line = re.sub(r'^[-•*]\s*', '', line).strip()

                        # Try to parse quantity, unit, and name
                        # Pattern: "number unit ingredient" or "number ingredient"
                        parts = line.split(' ', 2)
                        if len(parts) >= 2:
                            try:
                                # Try to parse the first part as quantity
                                quantity_str = parts[0]
                                quantity = float(Fraction(quantity_str))
                                if len(parts) == 3:
                                    unit, name = parts[1], parts[2]
                                else:
                                    unit, name = "", parts[1]
                            except:
                                # If parsing fails, treat as unit + name
                                quantity = 1.0
                                unit, name = parts[0], ' '.join(parts[1:])
                        else:
                            quantity, unit, name = 1.0, "", line

                        parsed_ingredients.append({
                            "name": name.strip().lower(),
                            "unit": unit.strip(),
                            "quantity": quantity
                        })

            # Parse directions - look for numbered steps
            parsed_directions = []
            directions_match = re.search(r'Directions:\s*\n(.*?)(?=\n\s*Nutrition|\n\s*Tags:|\Z)', recipe_text,
                                         re.DOTALL | re.IGNORECASE)

            if directions_match:
                directions_text = directions_match.group(1)
                for line in directions_text.strip().split('\n'):
                    line = line.strip()
                    if line and (re.match(r'^\d+\.', line) or line.startswith('-')):
                        # Remove numbering or bullet point
                        line = re.sub(r'^\d+\.\s*', '', line)
                        line = re.sub(r'^[-•*]\s*', '', line)
                        if line.strip():
                            parsed_directions.append(line.strip())

            # Parse nutrition macros - improved parsing
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

            # Parse tags
            tags = []
            tag_match = re.search(r'Tags:\s*(.+)', recipe_text, re.IGNORECASE)
            if tag_match:
                raw_tags = tag_match.group(1)
                tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]

            # Parse cuisine & diet
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
                # Calculate estimated cost from ingredients
                cost_estimate = round(
                    sum(ingredient_prices.get(i["name"], 1.00) * i["quantity"]
                        for i in parsed_ingredients),
                    2
                )

            # Build grocery list
            grocery_list = estimate_grocery_list(parsed_ingredients)

            parsed_recipes.append({
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
            })

            print(f"Parsed recipe {idx + 1}: {recipe_name}")
            print(f"  Ingredients: {len(parsed_ingredients)}")
            print(f"  Directions: {len(parsed_directions)}")
            print(f"  Macros: {macros}")

        # 5) Insert each recipe into Supabase
        for rec in parsed_recipes:
            try:
                insert_result = supabase.table("recipes").insert({
                    "user_id": req.user_id,
                    "title": rec["recipe_name"],
                    "ingredients": rec["ingredients"],
                    "directions": rec["directions"],
                    "tags": rec["tags"],
                    "cuisine": rec["cuisine"],
                    "diet": rec["diet"],
                    "macro_estimate": rec["macros"],
                    "cost_estimate": rec["cost_estimate"]
                }).execute()

                if insert_result.data:
                    rec["recipe_id"] = insert_result.data[0]["id"]

            except Exception as insert_error:
                print(f"Warning: Failed to insert recipe to database: {insert_error}")

        # 6) Return the three parsed recipe objects
        return {"recipes": parsed_recipes}

    except Exception as e:
        print(f"Error in generate_recipe_with_grocery: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recipes: {str(e)}")


@app.post("/log-meal")
def log_meal(req: LogMealRequest):
    try:
        # Use provided date or fallback to today's date
        log_date = req.date if req.date else str(date.today())

        # Insert the meal log into Supabase
        supabase.table("meal_logs").insert({
            "user_id": req.user_id,
            "recipe_id": req.recipe_id,
            "date": log_date
        }).execute()

        return {
            "status": "meal logged",
            "date": log_date
        }

    except Exception as e:
        return {"error": str(e)}

@app.get("/meal-log")
def get_meal_log(user_id: str = Query(..., description="User's unique identifier")):
    try:
        # Step 1: Fetch meal logs for the user
        logs = supabase.table("meal_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .execute().data

        recipe_ids = [log["recipe_id"] for log in logs]
        if not recipe_ids:
            return {"meals": []}

        # Step 2: Fetch related recipe data for macros and cost
        recipe_data = supabase.table("recipes") \
            .select("id, title, macro_estimate, cost_estimate") \
            .in_("id", recipe_ids) \
            .execute().data
        recipe_map = {r["id"]: r for r in recipe_data}

        # Step 3: Combine log and recipe data into user-readable format
        combined = []
        for log in logs:
            recipe = recipe_map.get(log["recipe_id"], {})
            combined.append({
                "title": recipe.get("title", "Unknown"),
                "date": log["date"],
                "macros": recipe.get("macro_estimate", {}),
                "cost": recipe.get("cost_estimate", 0.0)
            })

        return {"meals": combined}

    except Exception as e:
        return {"error": str(e)}

@app.get("/nutrition-summary")
def get_nutrition_summary(user_id: str = Query(..., description="User's unique identifier")):
    try:
        # Define date range: today and one week ago
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)

        # Fetch meal logs within date range for the user
        logs = supabase.table("meal_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .gte("date", str(week_ago)) \
            .lte("date", str(today)) \
            .execute().data

        recipe_ids = [log["recipe_id"] for log in logs]
        if not recipe_ids:
            return {"summary": {}, "message": "No meals logged this week."}

        # Fetch macro data for logged recipes
        recipes = supabase.table("recipes") \
            .select("id, macro_estimate") \
            .in_("id", recipe_ids) \
            .execute().data
        recipe_map = {r["id"]: r["macro_estimate"] for r in recipes}

        # Aggregate macros by day
        summary_by_day = {}
        for log in logs:
            day = log["date"]
            macros = recipe_map.get(log["recipe_id"], {})

            # Initialize if day is new
            if day not in summary_by_day:
                summary_by_day[day] = {k: 0.0 for k in ["calories", "protein", "carbs", "fat", "fiber"]}

            # Accumulate macros
            for k in summary_by_day[day]:
                summary_by_day[day][k] += float(macros.get(k, 0))

        return {"summary": summary_by_day}

    except Exception as e:
        return {"error": str(e)}



@app.get("/search-recipes")
def search_recipes(
    user_id: str = Query(..., description="User's unique identifier"),
    keyword: Optional[str] = Query(None, description="Search keyword for recipe title or ingredients"),
    max_cost: Optional[float] = Query(None, description="Maximum recipe cost filter"),
    tag: Optional[str] = Query(None, description="Tag filter (e.g., vegan, high-protein)"),
    cuisine: Optional[str] = Query(None, description="Cuisine type filter"),
    diet: Optional[str] = Query(None, description="Diet type filter"),
):
    try:
        # Step 1: Base query for user and optional cost
        query = supabase.table("recipes").select("*").eq("user_id", user_id)
        if max_cost is not None:
            query = query.lte("cost_estimate", max_cost)

        recipes = query.execute().data

        # Step 2: Apply fuzzy keyword match on title and ingredients
        if keyword:
            keyword_lower = keyword.lower()
            recipes = [
                r for r in recipes
                if fuzz.partial_ratio(keyword_lower, r["title"].lower()) > 80 or
                   any(fuzz.partial_ratio(keyword_lower, i["name"].lower()) > 80 for i in r.get("ingredients", []))
            ]

        # Step 3: Tag match
        if tag:
            tag_lower = tag.lower()
            recipes = [
                r for r in recipes
                if any(tag_lower in t.lower() for t in r.get("tags", []))
            ]

        # Step 4: Cuisine match
        if cuisine:
            cuisine_lower = cuisine.lower()
            recipes = [
                r for r in recipes
                if cuisine_lower in (r.get("cuisine") or "").lower()
            ]

        # Step 5: Diet match
        if diet:
            diet_lower = diet.lower()
            recipes = [
                r for r in recipes
                if diet_lower in (r.get("diet") or "").lower()
            ]

        return {
            "results": recipes,
            "count": len(recipes)
        }

    except Exception as e:
        return {"error": str(e)}
@app.post("/custom-entry")
def custom_entry(req: CustomEntryRequest):
    try:
        log_date = req.date if req.date else str(date.today())

        entry = {
            "user_id": req.user_id,
            "food_name": req.food_name,
            "calories": req.calories,
            "protein": req.protein,
            "carbs": req.carbs,
            "fat": req.fat,
            "fiber": req.fiber,
            "date": log_date
        }

        supabase.table("manual_logs").insert(entry).execute()

        return {
            "status": "manual entry logged",
            "entry": entry
        }
    except Exception as e:
        return {"error": str(e)}




# Add this new endpoint to your FastAPI app
@app.post("/generate-single-recipe")
def generate_single_recipe(req: SingleRecipeRequest):
    try:
        # 1) Fetch user preferences (same as before)
        pref_resp = supabase.table("user_preferences") \
            .select("budget, allergies, diet") \
            .eq("user_id", req.user_id) \
            .limit(1) \
            .execute()

        if pref_resp.data and len(pref_resp.data) > 0:
            prefs = pref_resp.data[0]
            try:
                user_budget = float(prefs.get("budget") or req.budget)
            except:
                user_budget = req.budget
            user_allergies = prefs.get("allergies") or ""
            user_diet = prefs.get("diet") or ""
        else:
            user_budget = req.budget
            user_allergies = ""
            user_diet = ""

        # 2) Build exclusion context from existing recipes
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

        # 3) Create prompt for single recipe
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

        Make the recipe completely unique and different from any existing ones.
        """.strip()

        # 4) Call OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8  # Higher temperature for more variety
        )
        recipe_text = response.choices[0].message.content.strip()

        print("Generated single recipe:")
        print(recipe_text[:200] + "...")

        # 5) Parse the single recipe (similar to existing parsing logic)
        # Extract recipe name
        recipe_name_match = re.search(r'RECIPE:\s*(.+)', recipe_text)
        recipe_name = recipe_name_match.group(1).strip() if recipe_name_match else "New Recipe"

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

        # Parse tags
        tags = []
        tag_match = re.search(r'Tags:\s*(.+)', recipe_text, re.IGNORECASE)
        if tag_match:
            raw_tags = tag_match.group(1)
            tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]

        # Parse cuisine & diet
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

        parsed_recipe = {
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

        # 6) Optionally insert into database
        try:
            insert_result = supabase.table("recipes").insert({
                "user_id": req.user_id,
                "title": recipe_name,
                "ingredients": parsed_ingredients,
                "directions": parsed_directions,
                "tags": tags,
                "cuisine": cuisine,
                "diet": diet,
                "macro_estimate": macros,
                "cost_estimate": cost_estimate
            }).execute()

            if insert_result.data:
                parsed_recipe["recipe_id"] = insert_result.data[0]["id"]

        except Exception as insert_error:
            print(f"Warning: Failed to insert recipe to database: {insert_error}")

        # 7) Return the single parsed recipe
        return {"recipe": parsed_recipe}

    except Exception as e:
        print(f"Error in generate_single_recipe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recipe: {str(e)}")


# Update the model to match what the frontend is sending
class GroceryItem(BaseModel):
    item_name: str
    quantity: float
    estimated_cost: float
    category: Optional[str] = "Recipe Generated"
    is_purchased: bool = False


class SaveGroceryListRequest(BaseModel):
    user_id: str
    grocery_items: list[GroceryItem]


# Add this new endpoint to your FastAPI app
@app.post("/save-grocery-list")
def save_grocery_list(req: SaveGroceryListRequest):
    try:
        if not req.user_id:
            raise HTTPException(status_code=400, detail="User ID is required")

        if not req.grocery_items or len(req.grocery_items) == 0:
            raise HTTPException(status_code=400, detail="No grocery items provided")

        print(f"Received request: user_id={req.user_id}, items={len(req.grocery_items)}")

        # Prepare grocery items for insertion
        grocery_items_to_insert = []
        updated_items_count = 0
        current_time = datetime.now().isoformat()

        for item in req.grocery_items:
            print(f"Processing item: {item.item_name}, quantity: {item.quantity}")

            # Check if item already exists in user's grocery list
            # Use 'name' field to check for existing items
            existing_item = supabase.table("grocery_items") \
                .select("id, quantity, estimated_cost") \
                .eq("user_id", req.user_id) \
                .eq("name", item.item_name) \
                .eq("is_purchased", False) \
                .limit(1) \
                .execute()

            print(f"Existing item query result: {existing_item}")

            if existing_item.data and len(existing_item.data) > 0:
                # Update existing item by adding quantities and costs
                existing = existing_item.data[0]
                current_quantity = float(existing.get("quantity", "0"))
                current_cost = float(existing.get("estimated_cost", 0))

                new_quantity = current_quantity + item.quantity
                new_cost = current_cost + item.estimated_cost

                print(f"Updating existing item: {item.item_name}, new_quantity: {new_quantity}, new_cost: {new_cost}")

                update_result = supabase.table("grocery_items") \
                    .update({
                    "quantity": str(new_quantity),  # Store as text since your column is text
                    "estimated_cost": round(new_cost, 2),
                    "updated_at": current_time
                }) \
                    .eq("id", existing["id"]) \
                    .execute()

                print(f"Update result: {update_result}")
                updated_items_count += 1
            else:
                # Add new item - match your exact table structure
                item_to_insert = {
                    "user_id": req.user_id,
                    "name": item.item_name,  # Required field (NOT NULL)
                    "quantity": str(item.quantity),  # Text field, so convert to string
                    "unit": "",  # Default empty string since it's text with default ''
                    "category": item.category or "Recipe Generated",  # Required field (NOT NULL)
                    "is_purchased": item.is_purchased,
                    "item_name": item.item_name,  # Also populate the item_name field
                    "estimated_cost": round(item.estimated_cost, 2),
                    "created_at": current_time,
                    "updated_at": current_time
                }

                print(f"Preparing to insert: {item_to_insert}")
                grocery_items_to_insert.append(item_to_insert)

        # Insert new items in batch
        inserted_items = []
        if grocery_items_to_insert:
            print(f"Inserting {len(grocery_items_to_insert)} items: {grocery_items_to_insert}")
            insert_result = supabase.table("grocery_items").insert(grocery_items_to_insert).execute()

            print(f"Insert result: {insert_result}")

            if hasattr(insert_result, 'error') and insert_result.error:
                print(f"Insert error: {insert_result.error}")
                raise HTTPException(status_code=500, detail=f"Database insert error: {insert_result.error}")

            if hasattr(insert_result, 'data') and insert_result.data:
                inserted_items = insert_result.data

        # Calculate total items affected
        total_items_affected = len(inserted_items)

        print(f"Summary: inserted={total_items_affected}, updated={updated_items_count}")

        return {
            "success": True,
            "message": f"Successfully processed {len(req.grocery_items)} grocery items",
            "inserted_items": total_items_affected,
            "updated_items": updated_items_count,
            "total_cost": round(sum(item.estimated_cost for item in req.grocery_items), 2)
        }

    except Exception as e:
        print(f"Error in save_grocery_list: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to save grocery list: {str(e)}")


# Optional: Add an endpoint to get the user's grocery list
@app.get("/grocery-list/{user_id}")
def get_grocery_list(user_id: str, include_purchased: bool = False):
    try:
        query = supabase.table("grocery_items") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True)

        if not include_purchased:
            query = query.eq("is_purchased", False)

        result = query.execute()

        return {
            "grocery_items": result.data or [],
            "total_items": len(result.data) if result.data else 0,
            "total_cost": round(sum(float(item.get("estimated_cost", 0)) for item in (result.data or [])), 2)
        }

    except Exception as e:
        print(f"Error in get_grocery_list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get grocery list: {str(e)}")


# Optional: Add an endpoint to mark items as purchased
@app.patch("/grocery-list/{item_id}/purchase")
def mark_item_purchased(item_id: int, user_id: str = Query(...)):
    try:
        result = supabase.table("grocery_items") \
            .update({
            "is_purchased": True,
            "purchased_at": datetime.now().isoformat()
        }) \
            .eq("id", item_id) \
            .eq("user_id", user_id) \
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Grocery item not found")

        return {"success": True, "message": "Item marked as purchased"}

    except Exception as e:
        print(f"Error in mark_item_purchased: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to mark item as purchased: {str(e)}")


import re
from typing import Dict, List


def normalize_ingredient_name(name: str) -> str:
    """
    Normalize ingredient names to consolidate similar items.
    """
    if not name:
        return 'unknown'

    # Convert to lowercase and remove extra whitespace
    normalized = name.lower().strip()

    # Remove common cooking descriptors that don't change the base ingredient
    descriptors_to_remove = [
        'diced', 'chopped', 'sliced', 'minced', 'crushed', 'grated',
        'fresh', 'dried', 'frozen', 'canned', 'cooked', 'raw',
        'boneless', 'skinless', 'lean', 'ground', 'whole',
        'large', 'medium', 'small', 'extra', 'jumbo',
        'organic', 'free-range', 'grass-fed'
    ]

    # Remove descriptors (use word boundaries to avoid partial matches)
    for descriptor in descriptors_to_remove:
        pattern = rf'\b{descriptor}\s+'
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

    # Handle specific ingredient mappings - RICE AND PASTA REMOVED
    ingredient_mappings = {
        # Chicken variations
        'chicken breast': 'chicken',
        'chicken thigh': 'chicken',
        'chicken thighs': 'chicken',
        'chicken leg': 'chicken',
        'chicken drumstick': 'chicken',
        'chicken wing': 'chicken',
        'chicken tender': 'chicken',

        # Beef variations
        'ground beef': 'beef',
        'beef chuck': 'beef',
        'beef sirloin': 'beef',
        'steak': 'beef',
        'beef steak': 'beef',

        # Pork variations
        'pork chop': 'pork',
        'pork shoulder': 'pork',
        'pork loin': 'pork',

        # Onion variations
        'yellow onion': 'onion',
        'white onion': 'onion',
        'red onion': 'onion',
        'sweet onion': 'onion',

        # Tomato variations
        'roma tomato': 'tomato',
        'cherry tomato': 'tomato',
        'grape tomato': 'tomato',
        'beefsteak tomato': 'tomato',

        # Pepper variations
        'bell pepper': 'bell pepper',
        'red bell pepper': 'bell pepper',
        'green bell pepper': 'bell pepper',
        'yellow bell pepper': 'bell pepper',

        # Garlic variations
        'garlic clove': 'garlic',
        'garlic bulb': 'garlic'

        # NOTE: Rice and pasta mappings have been removed so they stay distinct
        # (e.g., jasmine rice, basmati rice, penne, spaghetti will remain separate)
    }

    # Apply specific mappings
    for variant, base in ingredient_mappings.items():
        if variant in normalized:
            normalized = base
            break

    # Clean up any remaining extra spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    return normalized if normalized else name.lower()


def get_display_name(normalized_name: str, original_name: str) -> str:
    """
    Create a user-friendly display name for consolidated ingredients.
    """
    # Common ingredients that should use the normalized name
    common_ingredients = [
        'chicken', 'beef', 'pork', 'fish', 'turkey', 'lamb',
        'onion', 'tomato', 'garlic', 'carrot', 'celery',
        'rice', 'pasta', 'bread', 'cheese', 'milk', 'eggs'
    ]

    if normalized_name in common_ingredients:
        return normalized_name.capitalize()

    # For less common ingredients, use the original name but capitalized
    return original_name.capitalize()


# Updated save_grocery_list function with consolidation
@app.post("/save-grocery-list")
def save_grocery_list(req: SaveGroceryListRequest):
    try:
        if not req.user_id:
            raise HTTPException(status_code=400, detail="User ID is required")

        if not req.grocery_items or len(req.grocery_items) == 0:
            raise HTTPException(status_code=400, detail="No grocery items provided")

        print(f"Received request: user_id={req.user_id}, items={len(req.grocery_items)}")

        # First, consolidate the incoming items before processing
        consolidated_items = {}
        for item in req.grocery_items:
            normalized_name = normalize_ingredient_name(item.item_name)

            if normalized_name in consolidated_items:
                # Combine quantities and costs
                consolidated_items[normalized_name]['quantity'] += item.quantity
                consolidated_items[normalized_name]['estimated_cost'] += item.estimated_cost
                consolidated_items[normalized_name]['original_names'].append(item.item_name)
            else:
                consolidated_items[normalized_name] = {
                    'item_name': get_display_name(normalized_name, item.item_name),
                    'quantity': item.quantity,
                    'estimated_cost': item.estimated_cost,
                    'category': item.category or "Recipe Generated",
                    'is_purchased': False,
                    'original_names': [item.item_name]
                }

        # Now process the consolidated items
        grocery_items_to_insert = []
        updated_items_count = 0
        current_time = datetime.now().isoformat()

        for normalized_name, consolidated_item in consolidated_items.items():
            print(
                f"Processing consolidated item: {consolidated_item['item_name']}, quantity: {consolidated_item['quantity']}")

            # Check if a similar item already exists in user's grocery list
            # We'll check against both the normalized name and the display name
            existing_item_query = supabase.table("grocery_items") \
                .select("id, quantity, estimated_cost, name") \
                .eq("user_id", req.user_id) \
                .eq("is_purchased", False) \
                .execute()

            existing_item = None
            if existing_item_query.data:
                # Check if any existing item matches our normalized name
                for existing in existing_item_query.data:
                    existing_normalized = normalize_ingredient_name(existing.get("name", ""))
                    if existing_normalized == normalized_name:
                        existing_item = existing
                        break

            if existing_item:
                # Update existing item by adding quantities and costs
                current_quantity = float(existing_item.get("quantity", "0"))
                current_cost = float(existing_item.get("estimated_cost", 0))

                new_quantity = current_quantity + consolidated_item['quantity']
                new_cost = current_cost + consolidated_item['estimated_cost']

                print(
                    f"Updating existing item: {consolidated_item['item_name']}, new_quantity: {new_quantity}, new_cost: {new_cost}")

                update_result = supabase.table("grocery_items") \
                    .update({
                    "quantity": str(new_quantity),
                    "estimated_cost": round(new_cost, 2),
                    "updated_at": current_time
                }) \
                    .eq("id", existing_item["id"]) \
                    .execute()

                print(f"Update result: {update_result}")
                updated_items_count += 1
            else:
                # Add new consolidated item
                item_to_insert = {
                    "user_id": req.user_id,
                    "name": consolidated_item['item_name'],
                    "quantity": str(consolidated_item['quantity']),
                    "unit": "",
                    "category": consolidated_item['category'],
                    "is_purchased": consolidated_item['is_purchased'],
                    "item_name": consolidated_item['item_name'],
                    "estimated_cost": round(consolidated_item['estimated_cost'], 2),
                    "created_at": current_time,
                    "updated_at": current_time
                }

                print(f"Preparing to insert consolidated item: {item_to_insert}")
                grocery_items_to_insert.append(item_to_insert)

        # Insert new items in batch
        inserted_items = []
        if grocery_items_to_insert:
            print(f"Inserting {len(grocery_items_to_insert)} consolidated items")
            insert_result = supabase.table("grocery_items").insert(grocery_items_to_insert).execute()

            if hasattr(insert_result, 'error') and insert_result.error:
                print(f"Insert error: {insert_result.error}")
                raise HTTPException(status_code=500, detail=f"Database insert error: {insert_result.error}")

            if hasattr(insert_result, 'data') and insert_result.data:
                inserted_items = insert_result.data

        total_items_affected = len(inserted_items)
        total_original_items = len(req.grocery_items)
        total_consolidated_items = len(consolidated_items)

        print(f"Summary: {total_original_items} original items consolidated into {total_consolidated_items} items")
        print(f"Database: inserted={total_items_affected}, updated={updated_items_count}")

        return {
            "success": True,
            "message": f"Successfully consolidated {total_original_items} items into {total_consolidated_items} unique ingredients",
            "inserted_items": total_items_affected,
            "updated_items": updated_items_count,
            "total_cost": round(sum(item['estimated_cost'] for item in consolidated_items.values()), 2),
            "consolidation_summary": {
                "original_items": total_original_items,
                "consolidated_items": total_consolidated_items,
                "items_saved": total_original_items - total_consolidated_items
            }
        }

    except Exception as e:
        print(f"Error in save_grocery_list: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to save grocery list: {str(e)}")
    
# Helper function to analyze feedback and update preferences
def update_user_preferences_from_rating(user_id: str, rating: int, feedback_reason: str, recipe_data: dict):
    """
    Analyze the rating and feedback to update user preferences
    """
    try:
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
            
            # Add ingredients/cuisine to disliked based on feedback
            if feedback_reason == "Too many ingredients I don't like":
                # Add some ingredients to disliked list
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
            
            # Add to preferred (limit to top 3 ingredients per recipe to avoid noise)
            for ingredient in recipe_ingredients[:3]:
                if ingredient and ingredient not in preferred_ingredients and ingredient not in disliked_ingredients:
                    preferred_ingredients.append(ingredient)
                    
            if recipe_cuisine and recipe_cuisine not in preferred_cuisines:
                preferred_cuisines.append(recipe_cuisine)

        # Update or insert preferences
        preference_data = {
            "user_id": user_id,
            "disliked_ingredients": disliked_ingredients[-20:],  # Keep last 20 to avoid huge lists
            "disliked_cuisines": disliked_cuisines[-10:],
            "preferred_ingredients": preferred_ingredients[-20:],
            "preferred_cuisines": preferred_cuisines[-10:],
            "updated_at": datetime.now().isoformat()
        }
        
        if current_prefs.data:
            # Update existing
            supabase.table("user_preference_patterns") \
                .update(preference_data) \
                .eq("user_id", user_id) \
                .execute()
        else:
            # Insert new
            supabase.table("user_preference_patterns") \
                .insert(preference_data) \
                .execute()
                
        return True
        
    except Exception as e:
        print(f"Error updating user preferences: {e}")
        return False

@app.post("/rate-recipe")
def rate_recipe(req: RateRecipeRequest):
    """
    Rate a recipe and update user preferences based on the rating
    """
    try:
        # Validate rating
        if req.rating < 1 or req.rating > 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
            
        # For recipes that exist in database
        if req.recipe_id:
            # Validate UUID format
            try:
                uuid.UUID(req.recipe_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid recipe ID format")
            
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
            # Just update preferences without storing rating
            update_user_preferences_from_rating(
                req.user_id,
                req.rating,
                req.feedback_reason or "",
                req.recipe_data
            )
            
        return {
            "success": True,
            "message": "Rating submitted successfully",
            "preferences_updated": True
        }
        
    except Exception as e:
        print(f"Error in rate_recipe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit rating: {str(e)}")

@app.get("/user-preferences/{user_id}")
def get_user_preferences(user_id: str):
    """
    Get user's learned preferences for smart recipe generation
    """
    try:
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
        print(f"Error getting user preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get preferences: {str(e)}")

@app.get("/recipe-ratings/{user_id}")
def get_user_recipe_ratings(user_id: str, limit: int = 50):
    """
    Get user's recipe rating history
    """
    try:
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
        print(f"Error getting recipe ratings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get ratings: {str(e)}")