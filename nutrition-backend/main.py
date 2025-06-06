import os
import json
import re
from fractions import Fraction
import openai
from openai import OpenAI
from dotenv import load_dotenv
from fastapi import FastAPI, Body, Query
from pydantic import BaseModel
from supabase import create_client, Client
from datetime import datetime, timedelta,date

from typing import Optional
from rapidfuzz import fuzz
from typing import Optional
from fastapi import Query




# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

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
        # Check for existing recipe
        existing = supabase.table("recipes") \
            .select("*") \
            .eq("user_id", req.user_id) \
            .eq("title", req.title) \
            .execute()

        if existing.data:
            recipe = existing.data[0]
            grocery_list = estimate_grocery_list(recipe.get("ingredients", []))
            return {
                "recipe": recipe,
                "grocery_list": grocery_list,
                "note": "Recipe already existed in database."
            }

        # Prompt construction
        prompt = (
            f"Create a {req.title} recipe that costs less than ${req.budget:.2f}. "
            "Give a title to each meal. Include detailed step-by-step directions. "
            "Also include calories, protein, carbs, fat, and fiber in a bullet list. "
            "Include 3 to 5 tags describing the meal (e.g., 'high-protein', 'gluten-free', 'vegan'). "
            "Mention the cuisine type (e.g., 'Italian', 'Mexican', 'Indian') clearly as 'Cuisine: <name>'. "
            "Mention the diet type (e.g., 'Vegetarian', 'Keto', 'Paleo') clearly as 'Diet: <name>'."
        )

        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        content = response.choices[0].message.content

        # Parse ingredients
        parsed_ingredients = []
        ingredient_sections = re.findall(r"Ingredients:\n(.*?)(?:\n\n|Directions:)", content, re.DOTALL)
        for section in ingredient_sections:
            for line in section.strip().split("\n"):
                line = line.strip().lstrip("- ").strip()
                parts = line.split(" ", 2)
                if len(parts) == 3:
                    quantity_raw, unit, name = parts
                elif len(parts) == 2:
                    quantity_raw, name = parts
                    unit = ""
                else:
                    quantity_raw, unit, name = "1", "", line
                try:
                    quantity = float(Fraction(quantity_raw))
                except:
                    quantity = 1.0
                parsed_ingredients.append({
                    "name": name.strip().lower(),
                    "unit": unit.strip(),
                    "quantity": quantity
                })

        # Parse directions
        directions_match = re.search(r"Directions:\n(.*?)(?:\n\n|Calories:|Protein:|Carbs:|Fat:|Fiber:)", content, re.DOTALL)
        parsed_directions = []
        if directions_match:
            for step in directions_match.group(1).strip().split("\n"):
                parsed_directions.append(step.strip().lstrip("-").strip())

        # Parse other fields
        macros = parse_macros_from_text(content)

        tags = []
        tag_match = re.search(r"Tags:\s*(.+)", content, re.IGNORECASE)
        if tag_match:
            raw_tags = tag_match.group(1)
            tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]

        cuisine_match = re.search(r"Cuisine:\s*(.+)", content, re.IGNORECASE)
        cuisine = cuisine_match.group(1).strip() if cuisine_match else "Unknown"

        diet_match = re.search(r"Diet:\s*(.+)", content, re.IGNORECASE)
        diet = diet_match.group(1).strip() if diet_match else "Unknown"

        # Estimate cost
        cost_estimate = round(sum(
            ingredient_prices.get(i["name"], 1.00) * i["quantity"] for i in parsed_ingredients
        ), 2)

        # Construct full recipe object
        new_recipe = {
            "user_id": req.user_id,
            "title": req.title,
            "ingredients": parsed_ingredients,
            "directions": parsed_directions,
            "tags": tags,
            "cuisine": cuisine,
            "diet": diet,
            "macro_estimate": macros,
            "cost_estimate": cost_estimate
        }

        # Save to Supabase
        supabase.table("recipes").insert(new_recipe).execute()

        # Estimate grocery list
        grocery_list = estimate_grocery_list(parsed_ingredients)

        return {
            "recipe": new_recipe,
            "grocery_list": grocery_list,
            "note": "New recipe generated and saved."
        }

    except Exception as e:
        return {"error": str(e)}
# Fetch recipes for a user
@app.get("/recipes")
def get_user_recipes(user_id: str = Query(...)):
    try:
        # Query the Supabase 'recipes' table for the given user_id
        response = supabase.table("recipes") \
            .select("*") \
            .eq("user_id", user_id) \
            .execute()

        return {"recipes": response.data}

    except Exception as e:
        return {"error": str(e)}



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