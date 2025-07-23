# pantry.py - Pantry management router

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from database import supabase
import re

router = APIRouter()


# Inline models for pantry (since we don't have a models folder structure)
class PantryItem(BaseModel):
    name: str
    category: Optional[str] = "Uncategorized"
    quantity: float = 0
    unit: Optional[str] = ""
    expiration_date: Optional[date] = None
    cost_per_unit: Optional[float] = 0
    location: Optional[str] = "Pantry"  # Pantry, Fridge, Freezer
    brand: Optional[str] = None
    notes: Optional[str] = None
    barcode: Optional[str] = None


class AddPantryItemRequest(BaseModel):
    user_id: str
    items: List[PantryItem]


class UpdatePantryItemRequest(BaseModel):
    user_id: str
    item_id: int
    quantity: Optional[float] = None
    expiration_date: Optional[date] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class SubstitutionRequest(BaseModel):
    user_id: str
    missing_ingredients: List[str]
    dietary_restrictions: Optional[List[str]] = []
    budget_preference: Optional[str] = "medium"


def normalize_ingredient_name(ingredient: str) -> str:
    """Normalize ingredient names for better matching"""
    if not ingredient:
        return ""

    # Convert to lowercase and remove extra spaces
    normalized = ingredient.lower().strip()

    # Remove common descriptors
    descriptors = ['fresh', 'dried', 'frozen', 'canned', 'organic', 'raw', 'cooked',
                   'chopped', 'diced', 'sliced', 'minced', 'crushed', 'ground']

    for desc in descriptors:
        normalized = re.sub(rf'\b{desc}\b\s*', '', normalized)

    # Handle plurals and common variations
    replacements = {
        'tomatoes': 'tomato',
        'onions': 'onion',
        'potatoes': 'potato',
        'carrots': 'carrot',
        'apples': 'apple',
        'bananas': 'banana'
    }

    for plural, singular in replacements.items():
        if plural in normalized:
            normalized = normalized.replace(plural, singular)

    return normalized.strip()


@router.post("/pantry/add")
def add_pantry_items(req: AddPantryItemRequest):
    """Add items to user's pantry inventory"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        pantry_items = []
        current_time = datetime.now().isoformat()

        for item in req.items:
            pantry_item = {
                "user_id": req.user_id,
                "name": item.name,
                "category": item.category,
                "quantity": item.quantity,
                "unit": item.unit,
                "expiration_date": item.expiration_date.isoformat() if item.expiration_date else None,
                "cost_per_unit": item.cost_per_unit,
                "location": item.location,
                "brand": item.brand,
                "notes": item.notes,
                "barcode": item.barcode,
                "last_updated": current_time,
                "created_at": current_time
            }
            pantry_items.append(pantry_item)

        result = supabase.table("pantry_items").insert(pantry_items).execute()

        return {
            "success": True,
            "message": f"Added {len(pantry_items)} items to pantry",
            "items_added": len(result.data) if result.data else 0
        }

    except Exception as e:
        print(f"❌ Error adding pantry items: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add pantry items: {str(e)}")


@router.get("/pantry/{user_id}")
def get_pantry_inventory(user_id: str, location: str = Query(None), category: str = Query(None)):
    """Get user's pantry inventory with optional filtering"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        query = supabase.table("pantry_items").select("*").eq("user_id", user_id)

        if location:
            query = query.eq("location", location)
        if category:
            query = query.eq("category", category)

        result = query.order("name").execute()

        items = result.data or []

        # Calculate analytics
        total_value = sum(float(item.get("quantity", 0)) * float(item.get("cost_per_unit", 0)) for item in items)

        # Find items expiring soon (within 7 days)
        today = date.today()
        expiring_soon = []

        for item in items:
            if item.get("expiration_date"):
                exp_date = datetime.fromisoformat(item["expiration_date"]).date()
                if exp_date <= today + timedelta(days=7):
                    expiring_soon.append({
                        "id": item["id"],
                        "name": item["name"],
                        "expiration_date": item["expiration_date"],
                        "days_remaining": (exp_date - today).days
                    })

        # Group by categories and locations
        categories = {}
        locations = {}
        low_stock_items = []

        for item in items:
            cat = item.get("category", "Uncategorized")
            loc = item.get("location", "Pantry")
            qty = float(item.get("quantity", 0))

            categories[cat] = categories.get(cat, 0) + 1
            locations[loc] = locations.get(loc, 0) + 1

            # Consider items with quantity < 1 as low stock
            if qty < 1 and qty > 0:
                low_stock_items.append({
                    "id": item["id"],
                    "name": item["name"],
                    "quantity": qty,
                    "unit": item.get("unit", "")
                })

        return {
            "items": items,
            "analytics": {
                "total_items": len(items),
                "total_value": round(total_value, 2),
                "expiring_soon": expiring_soon,
                "categories": categories,
                "locations": locations,
                "low_stock_items": low_stock_items
            }
        }

    except Exception as e:
        print(f"❌ Error getting pantry inventory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get pantry inventory: {str(e)}")


@router.patch("/pantry/update/{item_id}")
def update_pantry_item(item_id: int, req: UpdatePantryItemRequest):
    """Update pantry item details"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        update_data = {"last_updated": datetime.now().isoformat()}

        if req.quantity is not None:
            update_data["quantity"] = req.quantity
        if req.expiration_date is not None:
            update_data["expiration_date"] = req.expiration_date.isoformat()
        if req.location is not None:
            update_data["location"] = req.location
        if req.notes is not None:
            update_data["notes"] = req.notes

        result = supabase.table("pantry_items") \
            .update(update_data) \
            .eq("id", item_id) \
            .eq("user_id", req.user_id) \
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Pantry item not found")

        return {"success": True, "message": "Pantry item updated"}

    except Exception as e:
        print(f"❌ Error updating pantry item: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update pantry item: {str(e)}")


@router.delete("/pantry/{item_id}")
def delete_pantry_item(item_id: int, user_id: str = Query(...)):
    """Delete pantry item"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        result = supabase.table("pantry_items") \
            .delete() \
            .eq("id", item_id) \
            .eq("user_id", user_id) \
            .execute()

        return {"success": True, "message": "Pantry item deleted"}

    except Exception as e:
        print(f"❌ Error deleting pantry item: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete pantry item: {str(e)}")


@router.post("/substitutions/suggest")
async def suggest_substitutions(req: SubstitutionRequest):
    """Get AI-powered smart substitution suggestions for missing ingredients"""
    try:
        # Try to import the substitution service
        try:
            from services.substitution_service import substitution_service
        except ImportError:
            print("⚠️ Substitution service not available, using fallback")
            return await _fallback_database_substitutions(req)

        # Get user's pantry for context
        user_pantry = []
        if supabase:
            pantry_result = supabase.table("pantry_items") \
                .select("*") \
                .eq("user_id", req.user_id) \
                .execute()
            user_pantry = pantry_result.data or []

        # Get AI-powered substitutions
        ai_substitutions = await substitution_service.get_smart_substitutions(
            missing_ingredients=req.missing_ingredients,
            dietary_restrictions=req.dietary_restrictions,
            budget_preference=req.budget_preference,
            user_pantry=user_pantry
        )

        # Format response for compatibility
        formatted_suggestions = []

        for sub_group in ai_substitutions:
            original = sub_group["original_ingredient"]

            for substitute in sub_group["substitutes"]:
                formatted_suggestions.append({
                    "original_ingredient": original,
                    "substitute_ingredient": substitute["substitute_ingredient"],
                    "conversion_ratio": substitute["conversion_ratio"],
                    "conversion_notes": substitute["conversion_notes"],
                    "confidence_score": substitute["confidence_score"],
                    "reason": substitute.get("reason", "AI recommendation"),
                    "dietary_benefits": substitute.get("dietary_benefits", []),
                    "cost_impact": substitute.get("cost_impact", "unknown"),
                    "flavor_impact": substitute.get("flavor_impact", "minimal"),
                    "difficulty": substitute.get("difficulty", "moderate"),
                    "pantry_alternative": substitute.get("pantry_alternative", False),
                    "source": substitute.get("source", "ai")
                })

        return {
            "substitutions": formatted_suggestions,
            "substitution_groups": ai_substitutions,
            "total_suggestions": len(formatted_suggestions),
            "ai_powered": True
        }

    except Exception as e:
        print(f"❌ Error suggesting AI substitutions: {str(e)}")
        # Fallback to basic database substitutions
        return await _fallback_database_substitutions(req)


async def _fallback_database_substitutions(req: SubstitutionRequest):
    """Fallback to database substitutions if AI fails"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        suggestions = []

        for ingredient in req.missing_ingredients:
            normalized_ingredient = normalize_ingredient_name(ingredient)

            # For fallback, create some basic substitutions
            basic_substitutions = {
                "milk": [{"substitute": "almond milk", "ratio": 1.0, "notes": "1:1 replacement"}],
                "butter": [{"substitute": "coconut oil", "ratio": 0.8, "notes": "Use 80% of butter amount"}],
                "eggs": [
                    {"substitute": "flax eggs", "ratio": 1.0, "notes": "1 tbsp ground flax + 3 tbsp water per egg"}],
                "heavy cream": [{"substitute": "coconut cream", "ratio": 1.0, "notes": "1:1 replacement"}],
                "cheese": [
                    {"substitute": "nutritional yeast", "ratio": 0.25, "notes": "Use 1/4 amount for umami flavor"}]
            }

            if normalized_ingredient in basic_substitutions:
                for sub in basic_substitutions[normalized_ingredient]:
                    suggestions.append({
                        "original_ingredient": ingredient,
                        "substitute_ingredient": sub["substitute"],
                        "conversion_ratio": sub["ratio"],
                        "conversion_notes": sub["notes"],
                        "confidence_score": 0.8,
                        "reason": "Basic substitution",
                        "source": "fallback",
                        "ai_powered": False
                    })

        return {
            "substitutions": suggestions,
            "total_suggestions": len(suggestions),
            "ai_powered": False,
            "fallback_used": True
        }

    except Exception as e:
        print(f"❌ Error in fallback substitutions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to suggest substitutions: {str(e)}")


@router.get("/pantry/analytics/{user_id}")
def get_pantry_analytics(user_id: str):
    """Get detailed pantry analytics"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        result = supabase.table("pantry_items") \
            .select("*") \
            .eq("user_id", user_id) \
            .execute()

        items = result.data or []

        # Calculate comprehensive analytics
        total_value = sum(float(item.get("quantity", 0)) * float(item.get("cost_per_unit", 0)) for item in items)

        # Expiring items analysis
        today = date.today()
        expiring_today = []
        expiring_week = []
        expiring_month = []

        for item in items:
            if item.get("expiration_date"):
                exp_date = datetime.fromisoformat(item["expiration_date"]).date()
                days_remaining = (exp_date - today).days

                item_info = {
                    "id": item["id"],
                    "name": item["name"],
                    "quantity": item["quantity"],
                    "unit": item.get("unit", ""),
                    "expiration_date": item["expiration_date"],
                    "days_remaining": days_remaining,
                    "value": float(item.get("quantity", 0)) * float(item.get("cost_per_unit", 0))
                }

                if days_remaining <= 0:
                    expiring_today.append(item_info)
                elif days_remaining <= 7:
                    expiring_week.append(item_info)
                elif days_remaining <= 30:
                    expiring_month.append(item_info)

        # Category and location breakdowns
        categories = {}
        locations = {}

        for item in items:
            cat = item.get("category", "Uncategorized")
            loc = item.get("location", "Pantry")
            qty = float(item.get("quantity", 0))
            value = qty * float(item.get("cost_per_unit", 0))

            if cat not in categories:
                categories[cat] = {"count": 0, "value": 0, "items": []}
            if loc not in locations:
                locations[loc] = {"count": 0, "value": 0, "items": []}

            categories[cat]["count"] += 1
            categories[cat]["value"] += value
            categories[cat]["items"].append(item["name"])

            locations[loc]["count"] += 1
            locations[loc]["value"] += value
            locations[loc]["items"].append(item["name"])

        # Low stock analysis
        low_stock = [
            {
                "id": item["id"],
                "name": item["name"],
                "quantity": item["quantity"],
                "unit": item.get("unit", ""),
                "category": item.get("category", "")
            }
            for item in items
            if float(item.get("quantity", 0)) < 1 and float(item.get("quantity", 0)) > 0
        ]

        return {
            "total_items": len(items),
            "total_value": round(total_value, 2),
            "expiring_analysis": {
                "expired_or_expiring_today": expiring_today,
                "expiring_this_week": expiring_week,
                "expiring_this_month": expiring_month,
                "total_expiring_value": sum(item["value"] for item in expiring_today + expiring_week)
            },
            "categories": categories,
            "locations": locations,
            "low_stock_items": low_stock,
            "recommendations": {
                "urgent_use": [item["name"] for item in expiring_today + expiring_week[:3]],
                "restock_needed": [item["name"] for item in low_stock[:5]],
                "highest_value_category": max(categories.items(), key=lambda x: x[1]["value"])[
                    0] if categories else None
            }
        }

    except Exception as e:
        print(f"❌ Error getting pantry analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get pantry analytics: {str(e)}")