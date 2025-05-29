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

# Request model
class RecipeRequest(BaseModel):
    title: str
    budget: float
    user_id: str

# Root check
@app.get("/")
def root():
    return {"api_key_loaded": bool(os.getenv("OPENAI_API_KEY"))}

# Generate recipe
@app.post("/generate-recipe")
@app.post("/generate-recipe")
def generate_recipe(req: RecipeRequest):
    existing = supabase.table("recipes") \
        .select("*") \
        .eq("user_id", req.user_id) \
        .eq("title", req.title) \
        .execute()

    if existing.data:
        return {"recipe": existing.data[0], "note": "Recipe already existed in database."}

    prompt = (
        f"Create a {req.title} recipe that costs less than ${req.budget:.2f}. "
        "Give a title to each meal. "
        "Include detailed step-by-step directions. "
        "Also include calories, protein, carbs, fat, and fiber in a bullet list. "
        "Include 3 to 5 tags describing the meal (e.g., 'high-protein', 'gluten-free', 'vegan'). "
        "Mention the cuisine type (e.g., 'Italian', 'Mexican', 'Indian') clearly as 'Cuisine: <name>'. "
        "Mention the diet type (e.g., 'Vegetarian', 'Keto', 'Paleo') clearly as 'Diet: <name>'."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        content = response.choices[0].message.content

        # Parse ingredients
        ingredient_sections = re.findall(r"Ingredients:\n(.*?)(?:\n\n|Directions:)", content, re.DOTALL)
        parsed_ingredients = []
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

        # Parse macros
        macros = {k: 0 for k in ["calories", "protein", "carbs", "fat", "fiber"]}
        for key in macros:
            match = re.search(fr"{key.capitalize()}: *([\d.]+)", content)
            if match:
                macros[key] = (match.group(1))

        # Parse tags
        tags = []
        tag_match = re.search(r"Tags:\s*(.+)", content, re.IGNORECASE)
        if tag_match:
            raw_tags = tag_match.group(1)
            tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]

        # Parse cuisine
        cuisine = None
        cuisine_match = re.search(r"Cuisine:\s*(.+)", content, re.IGNORECASE)
        if cuisine_match:
            cuisine = cuisine_match.group(1).strip()

        # Parse diet
        diet = None
        diet_match = re.search(r"Diet:\s*(.+)", content, re.IGNORECASE)
        if diet_match:
            diet = diet_match.group(1).strip()

        # Cost estimate
        fallback_price = 1.00
        cost_estimate = sum(
            ingredient_prices.get(item["name"], fallback_price) * item["quantity"]
            for item in parsed_ingredients
        )

        # Insert into Supabase
        supabase.table("recipes").insert({
            "user_id": req.user_id,
            "title": req.title,
            "ingredients": parsed_ingredients,
            "directions": parsed_directions,
            "tags": tags,
            "cuisine": cuisine,
            "diet": diet,
            "macro_estimate": macros,
            "cost_estimate": round(cost_estimate, 2)
        }).execute()

        return {
            "recipe_text": content,
            "ingredients": parsed_ingredients,
            "directions": parsed_directions,
            "macros": macros,
            "tags": tags,
            "cuisine": cuisine,
            "diet": diet,
            "cost_estimate": round(cost_estimate, 2)
        }

    except Exception as e:
        return {"error": str(e)}


# Grocery list estimate
@app.post("/grocery-list")
def generate_grocery_list(ingredients: list = Body(...)):
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
    return {"grocery_list": grocery_list}

# Combined endpoint
@app.post("/generate-recipe-with-grocery")
def generate_recipe_with_grocery(req: RecipeRequest):
    # Reuse logic from above
    result = generate_recipe(req)
    if "error" in result or "recipe_text" not in result:
        return result

    ingredients = result.get("ingredients", [])
    fallback_price = 1.00
    grocery_list = []
    for item in ingredients:
        name = item["name"]
        quantity = item["quantity"]
        unit_price = ingredient_prices.get(name, fallback_price)
        estimated_cost = round(unit_price * quantity, 2)
        grocery_list.append({
            "item": name,
            "quantity": quantity,
            "estimated_cost": estimated_cost
        })

    result["grocery_list"] = grocery_list
    return result

# Fetch recipes for a user
@app.get("/recipes")
def get_user_recipes(user_id: str = Query(...)):
    try:
        response = supabase.table("recipes").select("*").eq("user_id", user_id).execute()
        return {"recipes": response.data}
    except Exception as e:
        return {"error": str(e)}

# Meal logging
class LogMealRequest(BaseModel):
    user_id: str
    recipe_id: str
    date: Optional[str] = None  # Expect format YYYY-MM-DD


@app.post("/log-meal")
def log_meal(req: LogMealRequest):
    try:
        log_date = req.date if req.date else str(date.today())

        supabase.table("meal_logs").insert({
            "user_id": req.user_id,
            "recipe_id": req.recipe_id,
            "date": log_date
        }).execute()

        return {"status": "meal logged", "date": log_date}

    except Exception as e:
        return {"error": str(e)}

@app.get("/meal-log")
def get_meal_log(user_id: str = Query(...)):
    try:
        logs = supabase.table("meal_logs").select("*").eq("user_id", user_id).execute().data
        recipe_ids = [log["recipe_id"] for log in logs]

        if not recipe_ids:
            return {"meals": []}

        recipe_data = supabase.table("recipes") \
            .select("id, title, macro_estimate, cost_estimate") \
            .in_("id", recipe_ids) \
            .execute().data
        recipe_map = {r["id"]: r for r in recipe_data}

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
def get_nutrition_summary(user_id: str = Query(...)):
    try:
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)

        logs = supabase.table("meal_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .gte("date", str(week_ago)) \
            .lte("date", str(today)) \
            .execute().data

        recipe_ids = [log["recipe_id"] for log in logs]
        if not recipe_ids:
            return {"summary": {}, "message": "No meals logged this week."}

        recipes = supabase.table("recipes") \
            .select("id, macro_estimate") \
            .in_("id", recipe_ids) \
            .execute().data
        recipe_map = {r["id"]: r["macro_estimate"] for r in recipes}

        # Group macros by log date
        summary_by_day = {}
        for log in logs:
            day = log["date"]
            macros = recipe_map.get(log["recipe_id"], {})

            if day not in summary_by_day:
                summary_by_day[day] = {k: 0 for k in ["calories", "protein", "carbs", "fat", "fiber"]}

            for k in summary_by_day[day]:
                summary_by_day[day][k] += macros.get(k, 0)

        return {"summary": summary_by_day}

    except Exception as e:
        return {"error": str(e)}
@app.get("/search-recipes")
def search_recipes(
    user_id: str = Query(...),
    keyword: Optional[str] = Query(None),
    max_cost: Optional[float] = Query(None),
    tag: Optional[str] = Query(None),
    cuisine: Optional[str] = Query(None),
    diet: Optional[str] = Query(None),
):
    try:
        # Step 1: Basic query for user and cost
        query = supabase.table("recipes").select("*").eq("user_id", user_id)
        if max_cost is not None:
            query = query.lte("cost_estimate", max_cost)
        recipes = query.execute().data

        # Step 2: Optional filters
        if keyword:
            keyword_lower = keyword.lower()
            recipes = [
                r for r in recipes
                if fuzz.partial_ratio(keyword_lower, r["title"].lower()) > 80 or
                   any(fuzz.partial_ratio(keyword_lower, i["name"].lower()) > 80 for i in r.get("ingredients", []))
            ]

        if tag:
            tag_lower = tag.lower()
            recipes = [
                r for r in recipes
                if any(tag_lower in t.lower() for t in r.get("tags", []))
            ]

        if cuisine:
            cuisine_lower = cuisine.lower()
            recipes = [r for r in recipes if cuisine_lower in (r.get("cuisine") or "").lower()]

        if diet:
            diet_lower = diet.lower()
            recipes = [r for r in recipes if diet_lower in (r.get("diet") or "").lower()]

        return {"results": recipes, "count": len(recipes)}

    except Exception as e:
        return {"error": str(e)}