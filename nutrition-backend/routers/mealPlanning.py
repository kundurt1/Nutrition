from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from models.mealPlanningModels import SaveMealPlanRequest, GenerateGroceryFromMealPlanRequest
from database import supabase
import json

router = APIRouter()

@router.get("/meal-plans/{user_id}")
def get_meal_plans(user_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Get user's meal plans for a date range"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Default to current week if no dates provided
        if not start_date:
            today = date.today()
            start_of_week = today - timedelta(days=today.weekday())
            start_date = start_of_week.strftime('%Y-%m-%d')
        
        if not end_date:
            today = date.today()
            end_of_week = today + timedelta(days=(6 - today.weekday()))
            end_date = end_of_week.strftime('%Y-%m-%d')

        # Fetch meal plans from database
        result = supabase.table("meal_plans") \
            .select("*") \
            .eq("user_id", user_id) \
            .gte("plan_date", start_date) \
            .lte("plan_date", end_date) \
            .execute()

        meal_plans_data = result.data or []
        
        # Convert to frontend format
        meal_plans = {}
        for plan in meal_plans_data:
            date_key = plan["plan_date"]
            if date_key not in meal_plans:
                meal_plans[date_key] = []
            
            # Parse meals JSON
            meals = plan.get("meals", [])
            if isinstance(meals, str):
                try:
                    meals = json.loads(meals)
                except:
                    meals = []
            
            meal_plans[date_key].extend(meals)

        print(f"✅ Retrieved meal plans for user {user_id}: {len(meal_plans)} days planned")

        return {
            "meal_plans": meal_plans,
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            }
        }

    except Exception as e:
        print(f"❌ Error retrieving meal plans: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve meal plans: {str(e)}")

@router.post("/save-meal-plan")
def save_meal_plan(req: SaveMealPlanRequest):
    """Save or update meal plan for a specific date"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        print(f"Saving meal plan for user {req.user_id} on {req.date}")

        # Check if meal plan already exists for this date
        existing_result = supabase.table("meal_plans") \
            .select("id") \
            .eq("user_id", req.user_id) \
            .eq("plan_date", req.date) \
            .execute()

        meal_plan_data = {
            "user_id": req.user_id,
            "plan_date": req.date,
            "meals": req.meals,
            "updated_at": datetime.now().isoformat()
        }

        if existing_result.data and len(existing_result.data) > 0:
            # Update existing meal plan
            existing_id = existing_result.data[0]["id"]
            update_result = supabase.table("meal_plans") \
                .update(meal_plan_data) \
                .eq("id", existing_id) \
                .execute()
            
            print(f"✅ Updated meal plan for {req.date}")
        else:
            # Create new meal plan
            meal_plan_data["created_at"] = datetime.now().isoformat()
            insert_result = supabase.table("meal_plans") \
                .insert(meal_plan_data) \
                .execute()
            
            print(f"✅ Created new meal plan for {req.date}")

        return {
            "success": True,
            "message": f"Meal plan saved for {req.date}",
            "meals_count": len(req.meals)
        }

    except Exception as e:
        print(f"❌ Error saving meal plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save meal plan: {str(e)}")

@router.delete("/meal-plans/{user_id}")
def delete_meal_plan(user_id: str, date: str = Query(...)):
    """Delete meal plan for a specific date"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        result = supabase.table("meal_plans") \
            .delete() \
            .eq("user_id", user_id) \
            .eq("plan_date", date) \
            .execute()

        print(f"✅ Deleted meal plan for user {user_id} on {date}")

        return {
            "success": True,
            "message": f"Meal plan deleted for {date}"
        }

    except Exception as e:
        print(f"❌ Error deleting meal plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete meal plan: {str(e)}")

@router.get("/user-recipes/{user_id}")
def get_user_recipes(user_id: str, limit: int = 20, offset: int = 0):
    """Get user's previously generated recipes for meal planning"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Fetch user's recipes from database
        result = supabase.table("recipes") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .offset(offset) \
            .execute()

        recipes = result.data or []

        # Format recipes for frontend
        formatted_recipes = []
        for recipe in recipes:
            # Ensure cost_estimate is a number
            cost_estimate = recipe.get("cost_estimate", 0)
            if isinstance(cost_estimate, str):
                try:
                    cost_estimate = float(cost_estimate)
                except:
                    cost_estimate = 0.0

            formatted_recipe = {
                "id": recipe["id"],
                "recipe_name": recipe.get("title", "Unknown Recipe"),
                "title": recipe.get("title", "Unknown Recipe"),
                "cuisine": recipe.get("cuisine", "Unknown"),
                "cost_estimate": cost_estimate,
                "cost": cost_estimate,  # Alias for consistency
                "prep_time": recipe.get("prep_time", "30 min"),
                "cook_time": recipe.get("cook_time", "20 min"),
                "difficulty": recipe.get("difficulty", "Medium"),
                "macros": recipe.get("macro_estimate", {}),
                "calories": recipe.get("macro_estimate", {}).get("calories", 0),
                "ingredients": recipe.get("ingredients", []),
                "directions": recipe.get("directions", []),
                "tags": recipe.get("tags", []),
                "rating": 4.0,  # Default rating
                "created_at": recipe.get("created_at")
            }
            formatted_recipes.append(formatted_recipe)

        print(f"✅ Retrieved {len(formatted_recipes)} recipes for user {user_id}")

        return {
            "recipes": formatted_recipes,
            "total_count": len(formatted_recipes),
            "has_more": len(formatted_recipes) == limit
        }

    except Exception as e:
        print(f"❌ Error retrieving user recipes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve recipes: {str(e)}")

@router.post("/generate-grocery-from-meal-plan")
def generate_grocery_from_meal_plan(req: GenerateGroceryFromMealPlanRequest):
    """Generate grocery list from meal plan"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        print(f"Generating grocery list from meal plan for user {req.user_id}")

        # Consolidate ingredients from all planned meals
        ingredient_counts = {}
        total_meals = 0

        for date_key, meals in req.meal_plans.items():
            for meal in meals:
                total_meals += 1
                ingredients = meal.get("ingredients", [])
                
                for ingredient in ingredients:
                    ingredient_name = ingredient.get("name", "").lower().strip()
                    if not ingredient_name:
                        continue
                    
                    quantity = ingredient.get("quantity", 1)
                    unit = ingredient.get("unit", "")
                    
                    # Create a key for similar ingredients
                    ingredient_key = f"{ingredient_name}_{unit}".lower()
                    
                    if ingredient_key in ingredient_counts:
                        ingredient_counts[ingredient_key]["quantity"] += quantity
                    else:
                        ingredient_counts[ingredient_key] = {
                            "name": ingredient_name.title(),
                            "quantity": quantity,
                            "unit": unit,
                            "estimated_cost": estimate_ingredient_cost(ingredient_name, quantity)
                        }

        # Prepare grocery items for insertion
        grocery_items = []
        current_time = datetime.now().isoformat()

        for ingredient_data in ingredient_counts.values():
            grocery_item = {
                "user_id": req.user_id,
                "name": ingredient_data["name"],
                "item_name": ingredient_data["name"],
                "quantity": str(ingredient_data["quantity"]),
                "unit": ingredient_data["unit"],
                "category": "Meal Plan Generated",
                "estimated_cost": ingredient_data["estimated_cost"],
                "is_purchased": False,
                "created_at": current_time,
                "updated_at": current_time
            }
            grocery_items.append(grocery_item)

        # Insert grocery items
        if grocery_items:
            insert_result = supabase.table("grocery_items") \
                .insert(grocery_items) \
                .execute()
            
            items_added = len(insert_result.data) if insert_result.data else 0
        else:
            items_added = 0

        total_cost = sum(item["estimated_cost"] for item in grocery_items)

        print(f"✅ Generated grocery list: {items_added} items from {total_meals} planned meals")

        return {
            "success": True,
            "message": f"Generated grocery list from {total_meals} planned meals",
            "items_added": items_added,
            "total_cost": round(total_cost, 2),
            "meal_count": total_meals,
            "unique_ingredients": len(ingredient_counts)
        }

    except Exception as e:
        print(f"❌ Error generating grocery list from meal plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate grocery list: {str(e)}")

@router.get("/meal-plan-analytics/{user_id}")
def get_meal_plan_analytics(user_id: str, days: int = 30):
    """Get analytics for user's meal planning habits"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Fetch meal plans for analytics
        result = supabase.table("meal_plans") \
            .select("*") \
            .eq("user_id", user_id) \
            .gte("plan_date", start_date.strftime('%Y-%m-%d')) \
            .lte("plan_date", end_date.strftime('%Y-%m-%d')) \
            .execute()

        meal_plans = result.data or []

        # Calculate analytics
        total_planned_days = len(meal_plans)
        total_meals = 0
        cuisine_counts = {}
        cost_totals = []
        
        for plan in meal_plans:
            meals = plan.get("meals", [])
            if isinstance(meals, str):
                try:
                    meals = json.loads(meals)
                except:
                    meals = []
            
            daily_cost = 0
            for meal in meals:
                total_meals += 1
                
                # Count cuisines
                cuisine = meal.get("cuisine", "Unknown")
                cuisine_counts[cuisine] = cuisine_counts.get(cuisine, 0) + 1
                
                # Track costs
                cost = meal.get("cost_estimate", 0) or meal.get("cost", 0)
                daily_cost += cost
            
            if daily_cost > 0:
                cost_totals.append(daily_cost)

        # Calculate averages
        avg_meals_per_day = round(total_meals / max(total_planned_days, 1), 1)
        avg_daily_cost = round(sum(cost_totals) / max(len(cost_totals), 1), 2) if cost_totals else 0
        
        # Top cuisines
        top_cuisines = [
            {"cuisine": cuisine, "count": count}
            for cuisine, count in sorted(cuisine_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        # Planning consistency (percentage of days with plans)
        planning_consistency = round((total_planned_days / days) * 100, 1)

        print(f"✅ Generated meal plan analytics for user {user_id}")

        return {
            "analytics": {
                "total_planned_days": total_planned_days,
                "total_meals": total_meals,
                "avg_meals_per_day": avg_meals_per_day,
                "avg_daily_cost": avg_daily_cost,
                "planning_consistency": planning_consistency,
                "top_cuisines": top_cuisines,
                "total_cost": round(sum(cost_totals), 2),
                "date_range": {
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d'),
                    "days": days
                }
            }
        }

    except Exception as e:
        print(f"❌ Error generating meal plan analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate analytics: {str(e)}")

@router.get("/meal-plan-suggestions/{user_id}")
def get_meal_plan_suggestions(user_id: str):
    """Get smart suggestions for meal planning based on user history"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Get user's favorite recipes and cuisines
        recipes_result = supabase.table("recipes") \
            .select("title, cuisine, cost_estimate, macro_estimate, tags") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(50) \
            .execute()

        recipes = recipes_result.data or []

        # Analyze preferences
        cuisine_preferences = {}
        cost_range = []
        popular_tags = {}

        for recipe in recipes:
            # Track cuisine preferences
            cuisine = recipe.get("cuisine", "Unknown")
            cuisine_preferences[cuisine] = cuisine_preferences.get(cuisine, 0) + 1
            
            # Track cost preferences
            cost = recipe.get("cost_estimate", 0)
            if cost > 0:
                cost_range.append(cost)
            
            # Track popular tags
            tags = recipe.get("tags", [])
            for tag in tags:
                popular_tags[tag] = popular_tags.get(tag, 0) + 1

        # Generate suggestions
        suggestions = {
            "quick_meals": [
                "Try planning 20-minute meals for busy weekdays",
                "Consider meal prep on Sundays for the week"
            ],
            "budget_optimization": [],
            "variety_suggestions": [],
            "prep_time_tips": [
                "Batch cook grains and proteins on weekends",
                "Pre-chop vegetables for the week"
            ]
        }

        # Budget suggestions
        if cost_range:
            avg_cost = sum(cost_range) / len(cost_range)
            suggestions["budget_optimization"].append(
                f"Your average meal cost is ${avg_cost:.2f}. Consider batch cooking to reduce costs."
            )

        # Variety suggestions based on cuisines
        top_cuisines = sorted(cuisine_preferences.items(), key=lambda x: x[1], reverse=True)[:3]
        if len(top_cuisines) > 0:
            suggestions["variety_suggestions"].append(
                f"You love {top_cuisines[0][0]} cuisine! Try exploring {get_similar_cuisine(top_cuisines[0][0])} for variety."
            )

        print(f"✅ Generated meal plan suggestions for user {user_id}")

        return {
            "suggestions": suggestions,
            "preferences": {
                "top_cuisines": [{"cuisine": c, "count": count} for c, count in top_cuisines],
                "avg_cost": round(sum(cost_range) / len(cost_range), 2) if cost_range else 0,
                "popular_tags": [{"tag": tag, "count": count} for tag, count in 
                               sorted(popular_tags.items(), key=lambda x: x[1], reverse=True)[:5]]
            }
        }

    except Exception as e:
        print(f"❌ Error generating meal plan suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestions: {str(e)}")

def estimate_ingredient_cost(ingredient_name: str, quantity: float) -> float:
    """Estimate cost for an ingredient - basic implementation"""
    # This is a simplified cost estimation
    # In production, you'd want to integrate with grocery price APIs
    
    base_costs = {
        "chicken": 3.00,
        "beef": 5.00,
        "pork": 4.00,
        "fish": 6.00,
        "salmon": 8.00,
        "rice": 0.50,
        "pasta": 1.00,
        "bread": 2.00,
        "eggs": 0.25,
        "milk": 0.15,
        "cheese": 4.00,
        "tomato": 1.00,
        "onion": 0.75,
        "garlic": 2.00,
        "oil": 1.00,
        "butter": 3.00
    }
    
    # Find base cost for ingredient
    ingredient_lower = ingredient_name.lower()
    base_cost = 1.50  # Default cost per unit
    
    for key, cost in base_costs.items():
        if key in ingredient_lower:
            base_cost = cost
            break
    
    return round(base_cost * quantity, 2)

def get_similar_cuisine(cuisine: str) -> str:
    """Get similar cuisine suggestions"""
    cuisine_map = {
        "Italian": "Mediterranean",
        "Mexican": "Spanish",
        "Chinese": "Thai",
        "Indian": "Middle Eastern",
        "French": "European",
        "American": "British",
        "Thai": "Vietnamese",
        "Japanese": "Korean"
    }
    
    return cuisine_map.get(cuisine, "International")