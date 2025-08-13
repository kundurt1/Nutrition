from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta, timezone
from database import supabase
import json

from models.userModels import LogMealRequest

router = APIRouter()

class QuickLogRecipeRequest(BaseModel):
    """Request model for quick recipe logging"""
    user_id: str
    recipe_data: Dict[str, Any]
    date: Optional[str] = None

class CustomEntryRequest(BaseModel):
    """Request model for custom food entries"""
    user_id: str
    food_name: str
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: Optional[float] = 0
    date: Optional[str] = None

class NutritionDashboardRequest(BaseModel):
    """Request model for nutrition dashboard"""
    user_id: str
    days: Optional[int] = 7

class DeleteEntryRequest(BaseModel):
    """Request model for deleting entries"""
    user_id: str
    entry_id: str
    entry_type: str

DEFAULT_GOALS = {
    "daily_calories": 2000,
    "daily_protein": 150,
    "daily_carbs": 200,
    "daily_fat": 70,
    "daily_fiber": 25,
    "daily_budget": 30.00,
}

class GoalsPayload(BaseModel):
    daily_calories: Optional[int] = None
    daily_protein:  Optional[int] = None
    daily_carbs:    Optional[int] = None
    daily_fat:      Optional[int] = None
    daily_fiber:    Optional[int] = None
    daily_budget:   Optional[float] = None

@router.get("/users/{user_id}/goals")
def get_user_goals(user_id: str):
    try:
        res = supabase.table("user_goals").select("*").eq("user_id", user_id).single().execute()
        if res.data:
            return {"user_id": user_id, "goals": res.data}
        # not found -> return defaults (don’t insert yet)
        return {"user_id": user_id, "goals": {"user_id": user_id, **DEFAULT_GOALS}}
    except Exception as e:
        # if single() raises on not found, treat as defaults
        if "No rows" in str(e):
            return {"user_id": user_id, "goals": {"user_id": user_id, **DEFAULT_GOALS}}
        raise HTTPException(status_code=500, detail=f"Failed to fetch goals: {e}")

@router.put("/users/{user_id}/goals")
def upsert_user_goals(user_id: str, payload: GoalsPayload):
    try:
        # build the update dict, falling back to defaults if None
        incoming = {k: v for k, v in payload.dict().items() if v is not None}
        to_store = {**DEFAULT_GOALS, **incoming, "user_id": user_id, "updated_at": datetime.now(timezone.utc).isoformat()}

        res = supabase.table("user_goals").upsert(to_store, on_conflict="user_id").execute()
        if res.error:
            raise RuntimeError(res.error.message)
        return {"user_id": user_id, "goals": to_store}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save goals: {e}")
@router.post("/quick-log-recipe")
def quick_log_recipe(req: QuickLogRecipeRequest):
    """Quick log recipe from frontend - matches HomePage expectations"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        user_id = req.user_id
        recipe_data = req.recipe_data
        log_date = req.date if req.date else str(date.today())

        # FIX: Handle both macro_estimate and macros
        macros = recipe_data.get('macros') or recipe_data.get('macro_estimate', {})

        # Ensure macros is a dict
        if isinstance(macros, str):
            try:
                macros = json.loads(macros)
            except json.JSONDecodeError:
                macros = {}

        # Update recipe_data to always use 'macros' key
        recipe_data['macros'] = macros
        if 'macro_estimate' in recipe_data:
            del recipe_data['macro_estimate']

        def parse_macro_value(value):
            """Parse macro values that might be strings like '25g' or numbers"""
            if isinstance(value, str):
                numeric_str = ''.join(filter(lambda x: x.isdigit() or x == '.', str(value)))
                return float(numeric_str) if numeric_str else 0.0
            return float(value) if value else 0.0

        calories = float(macros.get('calories', 0)) if macros.get('calories') else 0.0
        protein = parse_macro_value(macros.get('protein', 0))
        carbs = parse_macro_value(macros.get('carbs', 0))
        fat = parse_macro_value(macros.get('fat', 0))
        fiber = parse_macro_value(macros.get('fiber', 0))
        cost = float(recipe_data.get('cost_estimate', 0)) if recipe_data.get('cost_estimate') else 0.0

        # Create nutrition log entry
        nutrition_entry = {
            "user_id": user_id,
            "recipe_name": recipe_data.get('recipe_name', 'Generated Recipe'),
            "recipe_data": recipe_data,  # Now always has 'macros' key
            "date": log_date,
            "calories": calories,
            "protein": protein,
            "carbs": carbs,
            "fat": fat,
            "fiber": fiber,
            "cost": cost,
            "cuisine": recipe_data.get('cuisine', 'Unknown'),
            "logged_at": datetime.now().isoformat()
        }

        # Insert into nutrition_logs table
        insert_result = supabase.table("nutrition_logs").insert(nutrition_entry).execute()

        if insert_result.data and len(insert_result.data) > 0:
            print(f"✅ Logged recipe '{recipe_data.get('recipe_name')}' for user {user_id}")

            return {
                "success": True,
                "message": "Recipe successfully logged to nutrition tracker",
                "log_id": insert_result.data[0]["id"],
                "nutrition_summary": {
                    "calories": calories,
                    "protein": f"{protein}g",
                    "cost": f"${cost:.2f}"
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to log nutrition data")

    except Exception as e:
        print(f"❌ Error logging recipe nutrition: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to log meal: {str(e)}")

def log_meal_enhanced(req: Dict[str, Any]):
    """Enhanced meal logging that handles complete recipe data"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        user_id = req.get("user_id")
        recipe_data = req.get("recipe_data", {})
        log_date = req.get("date", str(date.today()))

        if not user_id:
            raise HTTPException(status_code=400, detail="User ID is required")

        # --- Fix: ensure macros is always a dict ---
        macros = recipe_data.get('macros', {})
        if isinstance(macros, str):
            try:
                macros = json.loads(macros)
            except json.JSONDecodeError:
                macros = {}

        def parse_macro_value(value):
            """Parse macro values that might be strings like '25g' or numbers"""
            if isinstance(value, str):
                numeric_str = ''.join(filter(lambda x: x.isdigit() or x == '.', str(value)))
                return float(numeric_str) if numeric_str else 0.0
            return float(value) if value else 0.0

        calories = float(macros.get('calories', 0)) if macros.get('calories') else 0.0
        protein = parse_macro_value(macros.get('protein', 0))
        carbs = parse_macro_value(macros.get('carbs', 0))
        fat = parse_macro_value(macros.get('fat', 0))
        fiber = parse_macro_value(macros.get('fiber', 0))
        cost = float(recipe_data.get('cost_estimate', 0)) if recipe_data.get('cost_estimate') else 0.0

        # Create nutrition log entry
        nutrition_entry = {
            "user_id": user_id,
            "recipe_name": recipe_data.get('recipe_name', 'Generated Recipe'),
            "recipe_data": recipe_data,
            "date": log_date,
            "calories": calories,
            "protein": protein,
            "carbs": carbs,
            "fat": fat,
            "fiber": fiber,
            "cost": cost,
            "cuisine": recipe_data.get('cuisine', 'Unknown'),
            "logged_at": datetime.now().isoformat()
        }

        # Insert into nutrition_logs table
        insert_result = supabase.table("nutrition_logs").insert(nutrition_entry).execute()

        if insert_result.data and len(insert_result.data) > 0:
            print(f"✅ Logged recipe '{recipe_data.get('recipe_name')}' for user {user_id}")

            return {
                "success": True,
                "message": "Recipe successfully logged to nutrition tracker",
                "log_id": insert_result.data[0]["id"],
                "nutrition_summary": {
                    "calories": calories,
                    "protein": f"{protein}g",
                    "cost": f"${cost:.2f}"
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to log nutrition data")

    except Exception as e:
        print(f"❌ Error logging recipe nutrition: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to log meal: {str(e)}")
@router.post("/custom-entry")
def custom_entry(req: CustomEntryRequest):
    """Log custom food entry - used by nutrition tracking"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        log_date = req.date if req.date else str(date.today())

        entry_data = {
            "user_id": req.user_id,
            "food_name": req.food_name,
            "calories": req.calories,
            "protein": req.protein,
            "carbs": req.carbs,
            "fat": req.fat,
            "fiber": req.fiber,
            "date": log_date,
            "logged_at": datetime.now().isoformat()
        }

        insert_result = supabase.table("manual_logs").insert(entry_data).execute()

        if insert_result.data and len(insert_result.data) > 0:
            print(f"✅ Logged custom entry '{req.food_name}' for user {req.user_id}")

            return {
                "success": True,
                "status": "manual entry logged",
                "entry": {
                    "id": insert_result.data[0]["id"],
                    "food_name": req.food_name,
                    "calories": req.calories,
                    "date": log_date
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to log custom entry")

    except Exception as e:
        print(f"❌ Error in custom_entry: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to log custom entry: {str(e)}")

@router.get("/daily-nutrition")
def get_daily_nutrition(user_id: str = Query(...), date: str = Query(...)):
    """Get all nutrition entries for a specific user and date - matches frontend expectations"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        print(f"Getting daily nutrition for user {user_id} on {date}")

        # Fetch nutrition logs (recipe-based entries)
        nutrition_logs_result = supabase.table("nutrition_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("date", date) \
            .order("logged_at", desc=True) \
            .execute()

        # Fetch manual entries
        manual_logs_result = supabase.table("manual_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("date", date) \
            .order("logged_at", desc=True) \
            .execute()

        # Combine and format all entries exactly as frontend expects
        logs = []

        # Process nutrition logs (from recipes)
        for log in (nutrition_logs_result.data or []):
            logs.append({
                "id": log["id"],
                "type": "meal",
                "recipe_data": log.get("recipe_data", {}),
                "logged_at": log.get("logged_at"),
                "date": log["date"]
            })

        # Process manual logs
        for log in (manual_logs_result.data or []):
            logs.append({
                "id": log["id"],
                "type": "custom",
                "food_name": log["food_name"],
                "calories": log["calories"],
                "protein": log["protein"],
                "carbs": log["carbs"],
                "fat": log["fat"],
                "fiber": log.get("fiber", 0),
                "logged_at": log.get("logged_at"),
                "date": log["date"]
            })

        # Sort by logged_at timestamp
        logs.sort(key=lambda x: x.get("logged_at", ""), reverse=True)

        print(f"✅ Retrieved {len(logs)} nutrition entries for {date}")

        return {
            "logs": logs,
            "date": date,
            "total_entries": len(logs)
        }

    except Exception as e:
        print(f"❌ Error getting daily nutrition: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get daily nutrition: {str(e)}")

@router.get("/weekly-nutrition-summary/{user_id}")
def get_weekly_nutrition_summary(user_id: str, days: int = Query(7)):
    """Get nutrition summary for the past week - matches frontend expectations"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        print(f"Getting weekly nutrition summary for user {user_id} from {start_date} to {end_date}")

        # Get nutrition logs
        nutrition_logs = supabase.table("nutrition_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .gte("date", str(start_date)) \
            .lte("date", str(end_date)) \
            .execute()

        # Get manual logs
        manual_logs = supabase.table("manual_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .gte("date", str(start_date)) \
            .lte("date", str(end_date)) \
            .execute()

        # Calculate totals
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        total_fiber = 0
        total_cost = 0
        total_entries = 0

        # Add nutrition logs
        for log in (nutrition_logs.data or []):
            total_calories += log.get("calories", 0)
            total_protein += log.get("protein", 0)
            total_carbs += log.get("carbs", 0)
            total_fat += log.get("fat", 0)
            total_fiber += log.get("fiber", 0)
            total_cost += log.get("cost", 0)
            total_entries += 1

        # Add manual logs
        for log in (manual_logs.data or []):
            total_calories += log.get("calories", 0)
            total_protein += log.get("protein", 0)
            total_carbs += log.get("carbs", 0)
            total_fat += log.get("fat", 0)
            total_fiber += log.get("fiber", 0)
            total_entries += 1

        # Calculate averages
        avg_calories = total_calories / days if days > 0 else 0
        avg_protein = total_protein / days if days > 0 else 0
        avg_carbs = total_carbs / days if days > 0 else 0
        avg_fat = total_fat / days if days > 0 else 0
        avg_cost = total_cost / days if days > 0 else 0

        print(f"✅ Generated weekly nutrition summary for user {user_id}")

        # Format response to match frontend expectations
        return {
            "weekly_summary": {
                "daily_averages": {
                    "calories": round(avg_calories, 1),
                    "protein": round(avg_protein, 1),
                    "carbs": round(avg_carbs, 1),
                    "fat": round(avg_fat, 1),
                    "cost": round(avg_cost, 2)
                },
                "entries_logged": total_entries,
                "goal_compliance": {
                    "calories": round((avg_calories / 2000) * 100, 1),  # Assuming 2000 cal goal
                    "protein": round((avg_protein / 150) * 100, 1),  # Assuming 150g goal
                }
            }
        }

    except Exception as e:
        print(f"❌ Error getting weekly nutrition summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get weekly summary: {str(e)}")

@router.get("/nutrition-dashboard/{user_id}")
def get_nutrition_dashboard(user_id: str, days: int = Query(7)):
    """Get comprehensive nutrition dashboard data - matches frontend expectations"""
    try:
        import json  # Add this import

        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        today = date.today()

        # Get today's nutrition data DIRECTLY (not calling the endpoint function)
        # Fetch today's nutrition logs directly from database
        nutrition_logs_result = supabase.table("nutrition_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("date", str(today)) \
            .order("logged_at", desc=True) \
            .execute()

        # Fetch today's manual entries
        manual_logs_result = supabase.table("manual_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("date", str(today)) \
            .order("logged_at", desc=True) \
            .execute()

        # Build today's logs in the expected format
        today_logs = []

        # Process nutrition logs (from recipes)
        for log in (nutrition_logs_result.data or []):
            today_logs.append({
                "id": log["id"],
                "type": "meal",
                "recipe_data": log.get("recipe_data", {}),
                "logged_at": log.get("logged_at"),
                "date": log["date"]
            })

        # Process manual logs
        for log in (manual_logs_result.data or []):
            today_logs.append({
                "id": log["id"],
                "type": "custom",
                "food_name": log["food_name"],
                "calories": log["calories"],
                "protein": log["protein"],
                "carbs": log["carbs"],
                "fat": log["fat"],
                "fiber": log.get("fiber", 0),
                "logged_at": log.get("logged_at"),
                "date": log["date"]
            })

        # Create today_data structure that matches what the rest of the function expects
        today_data = {
            "logs": today_logs,
            "date": str(today),
            "total_entries": len(today_logs)
        }

        # Get weekly summary data DIRECTLY (not calling the endpoint function)
        end_date = today
        start_date = end_date - timedelta(days=days - 1)

        # Get weekly nutrition logs
        weekly_nutrition_logs = supabase.table("nutrition_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .gte("date", str(start_date)) \
            .lte("date", str(end_date)) \
            .execute()

        # Get weekly manual logs
        weekly_manual_logs = supabase.table("manual_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .gte("date", str(start_date)) \
            .lte("date", str(end_date)) \
            .execute()

        # Calculate weekly totals
        weekly_total_calories = 0
        weekly_total_protein = 0
        weekly_total_carbs = 0
        weekly_total_fat = 0
        weekly_total_cost = 0
        weekly_total_entries = 0

        # Add nutrition logs
        for log in (weekly_nutrition_logs.data or []):
            # Handle macros parsing for recipe logs
            if log.get("recipe_data") and log["recipe_data"].get("macros"):
                macros = log["recipe_data"]["macros"]

                # Parse macros if it's a string
                if isinstance(macros, str):
                    try:
                        import json
                        macros = json.loads(macros)
                    except (json.JSONDecodeError, ValueError):
                        macros = {}

                if isinstance(macros, dict):
                    weekly_total_calories += float(macros.get("calories", 0) or 0)
                    weekly_total_protein += float(str(macros.get("protein", "0") or "0").replace("g", ""))
                    weekly_total_carbs += float(str(macros.get("carbs", "0") or "0").replace("g", ""))
                    weekly_total_fat += float(str(macros.get("fat", "0") or "0").replace("g", ""))

                weekly_total_cost += float(log.get("cost_estimate", 0) or 0)
            else:
                # Fallback to direct fields if no recipe_data
                weekly_total_calories += log.get("calories", 0) or 0
                weekly_total_protein += log.get("protein", 0) or 0
                weekly_total_carbs += log.get("carbs", 0) or 0
                weekly_total_fat += log.get("fat", 0) or 0
                weekly_total_cost += log.get("cost", 0) or 0

            weekly_total_entries += 1

        # Add manual logs
        for log in (weekly_manual_logs.data or []):
            weekly_total_calories += log.get("calories", 0)
            weekly_total_protein += log.get("protein", 0)
            weekly_total_carbs += log.get("carbs", 0)
            weekly_total_fat += log.get("fat", 0)
            weekly_total_entries += 1

        # Calculate averages
        avg_calories = weekly_total_calories / days if days > 0 else 0
        avg_protein = weekly_total_protein / days if days > 0 else 0
        avg_carbs = weekly_total_carbs / days if days > 0 else 0
        avg_fat = weekly_total_fat / days if days > 0 else 0
        avg_cost = weekly_total_cost / days if days > 0 else 0

        # Create weekly data structure
        weekly_data = {
            "weekly_summary": {
                "daily_averages": {
                    "calories": round(avg_calories, 1),
                    "protein": round(avg_protein, 1),
                    "carbs": round(avg_carbs, 1),
                    "fat": round(avg_fat, 1),
                    "cost": round(avg_cost, 2)
                },
                "entries_logged": weekly_total_entries,
                "goal_compliance": {
                    "calories": round((avg_calories / 2000) * 100, 1),  # Assuming 2000 cal goal
                    "protein": round((avg_protein / 150) * 100, 1),  # Assuming 150g goal
                }
            }
        }

        # Calculate today's totals for the dashboard
        today_totals = {
            "calories": 0,
            "protein": 0,
            "carbs": 0,
            "fat": 0,
            "fiber": 0,
            "cost": 0
        }

        for log in today_data.get("logs", []):
            if log["type"] == "meal" and log.get("recipe_data"):
                # Handle both string and dict macros
                macros = log["recipe_data"].get("macros", {})

                # If macros is a string, try to parse it as JSON
                if isinstance(macros, str):
                    try:
                        import json
                        macros = json.loads(macros)
                    except (json.JSONDecodeError, ValueError):
                        # If JSON parsing fails, create empty dict
                        macros = {}

                # Now macros should be a dict, safely extract values
                if isinstance(macros, dict):
                    today_totals["calories"] += float(macros.get("calories", 0) or 0)
                    today_totals["protein"] += float(str(macros.get("protein", "0") or "0").replace("g", ""))
                    today_totals["carbs"] += float(str(macros.get("carbs", "0") or "0").replace("g", ""))
                    today_totals["fat"] += float(str(macros.get("fat", "0") or "0").replace("g", ""))
                    today_totals["fiber"] += float(str(macros.get("fiber", "0") or "0").replace("g", ""))

                today_totals["cost"] += float(log["recipe_data"].get("cost_estimate", 0) or 0)
            elif log["type"] == "custom":
                today_totals["calories"] += log.get("calories", 0) or 0
                today_totals["protein"] += log.get("protein", 0) or 0
                today_totals["carbs"] += log.get("carbs", 0) or 0
                today_totals["fat"] += log.get("fat", 0) or 0
                today_totals["fiber"] += log.get("fiber", 0) or 0

        print(f"✅ Generated nutrition dashboard for user {user_id}")

        return {
            "dashboard": {
                "today": today_totals,
                "weekly": weekly_data.get("weekly_summary", {}),
                "insights": {
                    "logging_streak": 1,  # Calculate this based on consecutive days
                    "total_meals_logged": len(today_data.get("logs", [])),
                    "favorite_cuisines": [],  # Add cuisine analysis
                    "days_tracked": days
                }
            }
        }

    except Exception as e:
        print(f"❌ Error getting nutrition dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get nutrition dashboard: {str(e)}")

@router.delete("/nutrition-entry/{log_id}")
def delete_nutrition_entry(log_id: int, user_id: str = Query(...), entry_type: str = Query(...)):
    """Delete a nutrition log entry (meal or custom) - matches frontend expectations"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        table_name = "nutrition_logs" if entry_type == "meal" else "manual_logs"

        result = supabase.table(table_name) \
            .delete() \
            .eq("id", log_id) \
            .eq("user_id", user_id) \
            .execute()

        print(f"✅ Deleted {entry_type} entry {log_id} for user {user_id}")

        return {
            "success": True,
            "message": f"{entry_type.title()} entry deleted successfully"
        }

    except Exception as e:
        print(f"❌ Error deleting nutrition entry: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete entry: {str(e)}")

@router.delete("/custom-entry/{entry_id}")
def delete_custom_entry(entry_id: int, user_id: str = Query(...), entry_type: str = Query(...)):
    """Delete a custom entry - matches frontend expectations"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        result = supabase.table("manual_logs") \
            .delete() \
            .eq("id", entry_id) \
            .eq("user_id", user_id) \
            .execute()

        print(f"✅ Deleted custom entry {entry_id} for user {user_id}")

        return {
            "success": True,
            "message": "Custom entry deleted successfully"
        }

    except Exception as e:
        print(f"❌ Error deleting custom entry: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete entry: {str(e)}")

# Additional endpoints for compatibility with existing meal logging system

@router.post("/log-meal-simple")
def log_meal_simple(req: LogMealRequest):
    """Simple meal logging with recipe ID for existing recipes"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        log_date = req.date if req.date else str(date.today())

        meal_log_data = {
            "user_id": req.user_id,
            "recipe_id": req.recipe_id,
            "date": log_date,
            "created_at": datetime.now().isoformat()
        }

        insert_result = supabase.table("meal_logs").insert(meal_log_data).execute()

        if insert_result.data and len(insert_result.data) > 0:
            print(f"✅ Logged meal for user {req.user_id} on {log_date}")

            return {
                "success": True,
                "status": "meal logged",
                "date": log_date,
                "meal_log_id": insert_result.data[0]["id"]
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to log meal")

    except Exception as e:
        print(f"❌ Error in log_meal_simple: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to log meal: {str(e)}")

@router.get("/meal-log")
def get_meal_log(user_id: str = Query(...), days: int = Query(30)):
    """Get user's meal log - used by HomePage.jsx for nutrition insights"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Fetch meal logs for the user within date range
        logs = supabase.table("meal_logs") \
            .select("*, recipes!inner(id, title, macro_estimate, cost_estimate, cuisine)") \
            .eq("user_id", user_id) \
            .gte("date", str(start_date)) \
            .lte("date", str(end_date)) \
            .order("date", desc=True) \
            .execute()

        meal_logs = logs.data or []

        # Format the response for frontend consumption
        formatted_meals = []
        for log in meal_logs:
            recipe = log.get("recipes", {})
            formatted_meal = {
                "id": log["id"],
                "title": recipe.get("title", "Unknown Recipe"),
                "date": log["date"],
                "macros": recipe.get("macro_estimate", {}),
                "cost": recipe.get("cost_estimate", 0.0),
                "cuisine": recipe.get("cuisine", "Unknown"),
                "logged_at": log.get("created_at")
            }
            formatted_meals.append(formatted_meal)

        print(f"✅ Retrieved {len(formatted_meals)} meal logs for user {user_id}")

        return {
            "meals": formatted_meals,
            "total_meals": len(formatted_meals),
            "date_range": {
                "start_date": str(start_date),
                "end_date": str(end_date),
                "days": days
            }
        }

    except Exception as e:
        print(f"❌ Error in get_meal_log: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get meal log: {str(e)}")

@router.get("/nutrition-summary")
def get_nutrition_summary(user_id: str = Query(...)):
    """Get nutrition summary - used by HomePage.jsx dashboard"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Define date ranges
        today = date.today()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Fetch nutrition logs for the past month
        nutrition_logs = supabase.table("nutrition_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .gte("date", str(month_ago)) \
            .lte("date", str(today)) \
            .execute()

        # Fetch manual logs
        manual_logs = supabase.table("manual_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .gte("date", str(month_ago)) \
            .lte("date", str(today)) \
            .execute()

        # Calculate nutrition metrics
        today_nutrition = 0
        week_nutrition = 0
        today_logs = []
        week_logs = []

        # Process nutrition logs
        for log in (nutrition_logs.data or []):
            log_date = datetime.strptime(log["date"], "%Y-%m-%d").date()
            calories = log.get("calories", 0)

            if log_date == today:
                today_nutrition += calories
                today_logs.append(log)
            if log_date >= week_ago:
                week_nutrition += calories
                week_logs.append(log)

        # Process manual logs
        for log in (manual_logs.data or []):
            log_date = datetime.strptime(log["date"], "%Y-%m-%d").date()
            calories = log.get("calories", 0)

            if log_date == today:
                today_nutrition += calories
                today_logs.append(log)
            if log_date >= week_ago:
                week_nutrition += calories
                week_logs.append(log)

        avg_calories_per_day = week_nutrition / 7 if week_logs else 0

        # Find favorite cuisines from nutrition logs
        cuisine_count = {}
        for log in (nutrition_logs.data or []):
            cuisine = log.get("cuisine", "Unknown")
            cuisine_count[cuisine] = cuisine_count.get(cuisine, 0) + 1

        favorite_cuisines = [
            {"cuisine": cuisine, "count": count}
            for cuisine, count in sorted(cuisine_count.items(), key=lambda x: x[1], reverse=True)[:3]
        ]

        print(f"✅ Generated nutrition summary for user {user_id}")

        return {
            "summary": {
                "today": {
                    "total_calories": round(today_nutrition),
                    "meals_logged": len(today_logs),
                    "custom_entries": len([log for log in today_logs if "food_name" in log])
                },
                "week": {
                    "total_calories": round(week_nutrition),
                    "avg_calories_per_day": round(avg_calories_per_day),
                    "meals_logged": len(week_logs),
                    "nutrition_breakdown": {
                        "protein": 0,  # Calculate from logs if needed
                        "carbs": 0,
                        "fat": 0,
                        "fiber": 0
                    }
                },
                "insights": {
                    "favorite_cuisines": favorite_cuisines,
                    "favorite_meals": [],  # Add if needed
                    "total_meals_month": len(nutrition_logs.data or []) + len(manual_logs.data or [])
                }
            }
        }

    except Exception as e:
        print(f"❌ Error in get_nutrition_summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get nutrition summary: {str(e)}")

@router.get("/custom-entries")
def get_custom_entries(user_id: str = Query(...), days: int = Query(7)):
    """Get user's custom food entries"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Fetch custom entries
        entries = supabase.table("manual_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .gte("date", str(start_date)) \
            .lte("date", str(end_date)) \
            .order("logged_at", desc=True) \
            .execute()

        custom_entries = entries.data or []

        print(f"✅ Retrieved {len(custom_entries)} custom entries for user {user_id}")

        return {
            "entries": custom_entries,
            "total_entries": len(custom_entries)
        }

    except Exception as e:
        print(f"❌ Error in get_custom_entries: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get custom entries: {str(e)}")


class AnalyzeMealRequest(BaseModel):
    """Request model for analyzing custom meal descriptions"""
    description: str
    user_id: str
    servings: Optional[int] = 1


class AnalyzeMealResponse(BaseModel):
    """Response model for analyzed meal nutrition"""
    food_name: str
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float
    confidence_score: float
    analysis_notes: Optional[str] = None


@router.post("/analyze-custom-meal")
async def analyze_custom_meal(req: AnalyzeMealRequest):
    """
    Analyze a custom meal description using OpenAI to extract nutritional information
    """
    try:
        # Validate input
        if not req.description or len(req.description.strip()) < 3:
            raise HTTPException(
                status_code=400,
                detail="Please provide a more detailed description of your meal"
            )

        # Initialize OpenAI service
        from services.enhanced_openai_service import EnhancedOpenAIService
        openai_service = EnhancedOpenAIService()

        # Create the analysis prompt
        prompt = f"""
        Analyze the following meal/food description and provide accurate nutritional information.

        Description: "{req.description}"
        Servings: {req.servings}

        Provide the nutritional breakdown PER SERVING in this exact JSON format:
        {{
            "food_name": "concise name for the meal",
            "calories": number,
            "protein": number (in grams),
            "carbs": number (in grams),
            "fat": number (in grams),
            "fiber": number (in grams),
            "confidence_score": number between 0 and 1 (how confident you are in the accuracy),
            "analysis_notes": "brief note about assumptions made or tips for accuracy"
        }}

        Guidelines:
        - Be as accurate as possible based on typical portions and preparations
        - If the description mentions specific quantities, use those
        - If quantities are vague, use standard serving sizes
        - Consider cooking methods (fried, grilled, etc.) in your calculations
        - The confidence score should reflect how detailed the description is
        - Return ONLY the JSON object, no additional text
        """

        # Call OpenAI API
        try:
            response = await openai_service.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a nutrition expert that analyzes food descriptions and provides accurate nutritional information. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent nutritional data
                max_tokens=500
            )

            # Parse the response
            import json
            response_text = response.choices[0].message.content.strip()

            # Clean up response if needed (remove markdown code blocks if present)
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()

            # Parse JSON response
            nutrition_data = json.loads(response_text)

            # Validate and sanitize the data
            nutrition_data['calories'] = max(0, float(nutrition_data.get('calories', 0)))
            nutrition_data['protein'] = max(0, float(nutrition_data.get('protein', 0)))
            nutrition_data['carbs'] = max(0, float(nutrition_data.get('carbs', 0)))
            nutrition_data['fat'] = max(0, float(nutrition_data.get('fat', 0)))
            nutrition_data['fiber'] = max(0, float(nutrition_data.get('fiber', 0)))
            nutrition_data['confidence_score'] = min(1, max(0, float(nutrition_data.get('confidence_score', 0.7))))

            # Log the analysis for debugging
            print(f"✅ Analyzed meal: {nutrition_data['food_name']} - Confidence: {nutrition_data['confidence_score']}")

            return {
                "success": True,
                "nutrition": nutrition_data,
                "message": "Meal analyzed successfully"
            }

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse OpenAI response: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to parse nutritional information. Please try again with a clearer description."
            )
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to analyze meal. Please try again."
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error analyzing custom meal: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze meal: {str(e)}"
        )


@router.post("/save-analyzed-meal")
async def save_analyzed_meal(req: Dict[str, Any]):
    """
    Save an analyzed meal to the database after user confirmation/editing
    """
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Extract data from request
        user_id = req.get('user_id')
        nutrition = req.get('nutrition', {})
        log_date = req.get('date', str(date.today()))

        # Prepare entry data
        entry_data = {
            "user_id": user_id,
            "food_name": nutrition.get('food_name', 'Custom Meal'),
            "calories": float(nutrition.get('calories', 0)),
            "protein": float(nutrition.get('protein', 0)),
            "carbs": float(nutrition.get('carbs', 0)),
            "fat": float(nutrition.get('fat', 0)),
            "fiber": float(nutrition.get('fiber', 0)),
            "date": log_date,
            "logged_at": datetime.now().isoformat(),
            "source": "ai_analyzed",  # Mark as AI-analyzed
            "confidence_score": nutrition.get('confidence_score', 0.7)
        }

        # Insert into manual_logs table
        insert_result = supabase.table("manual_logs").insert(entry_data).execute()

        if insert_result.data and len(insert_result.data) > 0:
            print(f"✅ Saved analyzed meal '{entry_data['food_name']}' for user {user_id}")

            return {
                "success": True,
                "message": "Meal saved successfully",
                "entry": {
                    "id": insert_result.data[0]["id"],
                    "food_name": entry_data['food_name'],
                    "calories": entry_data['calories'],
                    "date": log_date
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save meal")

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error saving analyzed meal: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save meal: {str(e)}"
        )