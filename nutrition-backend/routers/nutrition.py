from fastapi import APIRouter, HTTPException, Query
from models.userModels import LogMealRequest, CustomEntryRequest
from database import supabase
from datetime import datetime, timedelta, date
from typing import Optional

router = APIRouter()

@router.post("/log-meal")
def log_meal(req: LogMealRequest):
    """Log a meal - used by meal tracking functionality"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Use provided date or fallback to today's date
        log_date = req.date if req.date else str(date.today())

        # Insert the meal log into Supabase
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
        print(f"❌ Error in log_meal: {str(e)}")
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

        # Fetch meal logs with recipe data for the past month
        logs = supabase.table("meal_logs") \
            .select("*, recipes!inner(macro_estimate, cuisine, title)") \
            .eq("user_id", user_id) \
            .gte("date", str(month_ago)) \
            .lte("date", str(today)) \
            .execute()

        meal_logs = logs.data or []

        # Calculate nutrition metrics
        today_meals = [log for log in meal_logs if log["date"] == str(today)]
        week_meals = [log for log in meal_logs if log["date"] >= str(week_ago)]

        # Calculate calories
        total_calories_today = sum(
            log["recipes"]["macro_estimate"].get("calories", 0) 
            for log in today_meals 
            if log["recipes"] and log["recipes"]["macro_estimate"]
        )

        total_calories_week = sum(
            log["recipes"]["macro_estimate"].get("calories", 0) 
            for log in week_meals 
            if log["recipes"] and log["recipes"]["macro_estimate"]
        )

        avg_calories_per_day = round(total_calories_week / 7) if week_meals else 0

        # Calculate macro breakdown for the week
        nutrition_breakdown = {"protein": 0, "carbs": 0, "fat": 0, "fiber": 0}
        
        for log in week_meals:
            if log["recipes"] and log["recipes"]["macro_estimate"]:
                macros = log["recipes"]["macro_estimate"]
                for key in nutrition_breakdown.keys():
                    value = macros.get(key, "0g")
                    # Extract numeric value from string like "25g"
                    if isinstance(value, str):
                        numeric_value = float(''.join(filter(str.isdigit, value))) if any(c.isdigit() for c in value) else 0
                    else:
                        numeric_value = float(value) if value else 0
                    nutrition_breakdown[key] += numeric_value

        # Round the nutrition values
        for key in nutrition_breakdown:
            nutrition_breakdown[key] = round(nutrition_breakdown[key])

        # Find favorite cuisines
        cuisine_count = {}
        for log in meal_logs:
            if log["recipes"] and log["recipes"]["cuisine"]:
                cuisine = log["recipes"]["cuisine"]
                cuisine_count[cuisine] = cuisine_count.get(cuisine, 0) + 1

        favorite_cuisines = [
            {"cuisine": cuisine, "count": count}
            for cuisine, count in sorted(cuisine_count.items(), key=lambda x: x[1], reverse=True)[:3]
        ]

        # Find favorite meals (most logged recipes)
        meal_count = {}
        for log in meal_logs:
            if log["recipes"] and log["recipes"]["title"]:
                title = log["recipes"]["title"]
                meal_count[title] = meal_count.get(title, 0) + 1

        favorite_meals = [
            {"title": title, "count": count}
            for title, count in sorted(meal_count.items(), key=lambda x: x[1], reverse=True)[:3]
        ]

        # Fetch custom entries for today
        custom_entries = supabase.table("manual_logs") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("date", str(today)) \
            .execute()

        custom_calories_today = sum(
            entry.get("calories", 0) for entry in (custom_entries.data or [])
        )

        print(f"✅ Generated nutrition summary for user {user_id}")

        return {
            "summary": {
                "today": {
                    "total_calories": round(total_calories_today + custom_calories_today),
                    "meals_logged": len(today_meals),
                    "custom_entries": len(custom_entries.data or [])
                },
                "week": {
                    "total_calories": round(total_calories_week),
                    "avg_calories_per_day": avg_calories_per_day,
                    "meals_logged": len(week_meals),
                    "nutrition_breakdown": nutrition_breakdown
                },
                "insights": {
                    "favorite_cuisines": favorite_cuisines,
                    "favorite_meals": favorite_meals,
                    "total_meals_month": len(meal_logs)
                }
            }
        }

    except Exception as e:
        print(f"❌ Error in get_nutrition_summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get nutrition summary: {str(e)}")

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
            "created_at": datetime.now().isoformat()
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
            .order("date", desc=True) \
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

@router.delete("/meal-log/{meal_log_id}")
def delete_meal_log(meal_log_id: int, user_id: str = Query(...)):
    """Delete a meal log entry"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        result = supabase.table("meal_logs") \
            .delete() \
            .eq("id", meal_log_id) \
            .eq("user_id", user_id) \
            .execute()

        print(f"✅ Deleted meal log {meal_log_id} for user {user_id}")

        return {
            "success": True,
            "message": "Meal log deleted successfully"
        }

    except Exception as e:
        print(f"❌ Error in delete_meal_log: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete meal log: {str(e)}")

@router.delete("/custom-entry/{entry_id}")
def delete_custom_entry(entry_id: int, user_id: str = Query(...)):
    """Delete a custom food entry"""
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
        print(f"❌ Error in delete_custom_entry: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete custom entry: {str(e)}")

# Additional endpoint for dashboard stats
@router.get("/dashboard-stats/{user_id}")
def get_dashboard_stats(user_id: str):
    """Get comprehensive dashboard statistics for HomePage.jsx"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Get recipe count
        recipes_result = supabase.table("recipes") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .execute()

        total_recipes = recipes_result.count if hasattr(recipes_result, 'count') else 0

        # Get grocery items count (unpurchased)
        grocery_result = supabase.table("grocery_items") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .eq("is_purchased", False) \
            .execute()

        total_grocery_items = grocery_result.count if hasattr(grocery_result, 'count') else 0

        # Get favorites count
        favorites_result = supabase.table("favorites") \
            .select("id", count="exact") \
            .eq("user_id", user_id) \
            .execute()

        total_favorites = favorites_result.count if hasattr(favorites_result, 'count') else 0

        # Get recent favorites
        recent_favorites = supabase.table("favorites") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("favorited_at", desc=True) \
            .limit(5) \
            .execute()

        # Get today's calories from nutrition summary
        nutrition_summary = get_nutrition_summary(user_id)
        today_calories = nutrition_summary["summary"]["today"]["total_calories"]

        print(f"✅ Generated dashboard stats for user {user_id}")

        return {
            "stats": {
                "total_recipes": total_recipes,
                "total_grocery_items": total_grocery_items,
                "total_favorites": total_favorites,
                "today_calories": today_calories
            },
            "recent_favorites": recent_favorites.data or [],
            "nutrition_insights": nutrition_summary["summary"]
        }

    except Exception as e:
        print(f"❌ Error in get_dashboard_stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")