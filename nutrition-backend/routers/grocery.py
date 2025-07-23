# grocery.py - Fixed import paths

from fastapi import APIRouter, HTTPException, Query
from models.groceryModels import SaveGroceryListRequest
# Fix: Add the SmartGroceryListRequest to your existing groceryModels.py
# OR create the model inline if it doesn't exist
from database import supabase
from datetime import datetime
import re
from typing import Dict, List

router = APIRouter()

# Define SmartGroceryListRequest inline if not in models
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class SmartGroceryListRequest(BaseModel):
    user_id: str
    recipe_ingredients: List[Dict[str, Any]]
    check_pantry: bool = True
    suggest_substitutions: bool = True
    optimize_for_budget: bool = False


def normalize_ingredient_name(ingredient: str) -> str:
    """Normalize ingredient names for better matching"""
    if not ingredient:
        return 'unknown'

    normalized = ingredient.lower().strip()

    # Remove common cooking descriptors
    descriptors_to_remove = [
        'diced', 'chopped', 'sliced', 'minced', 'crushed', 'grated',
        'fresh', 'dried', 'frozen', 'canned', 'cooked', 'raw',
        'boneless', 'skinless', 'lean', 'ground', 'whole',
        'large', 'medium', 'small', 'extra', 'jumbo',
        'organic', 'free-range', 'grass-fed'
    ]

    for descriptor in descriptors_to_remove:
        pattern = rf'\b{descriptor}\s+'
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

    # Handle specific ingredient mappings
    ingredient_mappings = {
        'chicken breast': 'chicken',
        'chicken thigh': 'chicken',
        'chicken thighs': 'chicken',
        'ground beef': 'beef',
        'beef chuck': 'beef',
        'yellow onion': 'onion',
        'white onion': 'onion',
        'red onion': 'onion',
        'roma tomato': 'tomato',
        'cherry tomato': 'tomato',
        'bell pepper': 'bell pepper',
        'red bell pepper': 'bell pepper',
        'garlic clove': 'garlic',
    }

    for variant, base in ingredient_mappings.items():
        if variant in normalized:
            normalized = base
            break

    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized if normalized else ingredient.lower()


def get_display_name(normalized_name: str, original_name: str) -> str:
    """Create a user-friendly display name for consolidated ingredients."""
    common_ingredients = [
        'chicken', 'beef', 'pork', 'fish', 'turkey', 'lamb',
        'onion', 'tomato', 'garlic', 'carrot', 'celery',
        'rice', 'pasta', 'bread', 'cheese', 'milk', 'eggs'
    ]

    if normalized_name in common_ingredients:
        return normalized_name.capitalize()

    return original_name.capitalize()


def check_pantry_availability(user_id: str, ingredient_name: str) -> Dict:
    """Check if ingredient is available in user's pantry"""
    try:
        if not supabase:
            return {"available": False, "quantity": 0}

        normalized_name = normalize_ingredient_name(ingredient_name)

        # Search pantry for this ingredient
        result = supabase.table("pantry_items") \
            .select("*") \
            .eq("user_id", user_id) \
            .execute()

        for item in result.data or []:
            item_normalized = normalize_ingredient_name(item.get("name", ""))
            if item_normalized == normalized_name:
                quantity = float(item.get("quantity", 0))
                if quantity > 0:
                    return {
                        "available": True,
                        "quantity": quantity,
                        "unit": item.get("unit", ""),
                        "location": item.get("location", "Pantry"),
                        "pantry_item_id": item.get("id")
                    }

        return {"available": False, "quantity": 0}

    except Exception as e:
        print(f"❌ Error checking pantry: {str(e)}")
        return {"available": False, "quantity": 0}


@router.post("/save-grocery-list")
def save_grocery_list(req: SaveGroceryListRequest):
    """Save consolidated grocery list with pantry checking - FIXED VERSION"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        if not req.user_id:
            raise HTTPException(status_code=400, detail="User ID is required")

        if not req.grocery_items or len(req.grocery_items) == 0:
            raise HTTPException(status_code=400, detail="No grocery items provided")

        print(f"🛒 Processing {len(req.grocery_items)} grocery items for user {req.user_id}")

        # Debug: Print incoming items to identify the bug
        for i, item in enumerate(req.grocery_items):
            print(f"Item {i}: {item}")

        # First, consolidate the incoming items
        consolidated_items = {}
        for item in req.grocery_items:
            # FIX: Handle different possible field names from recipes
            item_name = (
                item.item_name if hasattr(item, 'item_name') and item.item_name else
                item.item if hasattr(item, 'item') and item.item else
                item.name if hasattr(item, 'name') and item.name else
                "Unknown Item"
            )

            quantity = (
                item.quantity if hasattr(item, 'quantity') and item.quantity else 1
            )

            estimated_cost = (
                item.estimated_cost if hasattr(item, 'estimated_cost') and item.estimated_cost else 0
            )

            category = (
                item.category if hasattr(item, 'category') and item.category else "Recipe Generated"
            )

            print(f"📝 Processing item: {item_name}, qty: {quantity}, cost: {estimated_cost}")

            normalized_name = normalize_ingredient_name(item_name)

            # Check pantry availability
            pantry_info = check_pantry_availability(req.user_id, item_name)

            if normalized_name in consolidated_items:
                consolidated_items[normalized_name]['quantity'] += float(quantity)
                consolidated_items[normalized_name]['estimated_cost'] += float(estimated_cost)
                consolidated_items[normalized_name]['original_names'].append(item_name)
            else:
                consolidated_items[normalized_name] = {
                    'item_name': get_display_name(normalized_name, item_name),
                    'quantity': float(quantity),
                    'estimated_cost': float(estimated_cost),
                    'category': category,
                    'is_purchased': False,
                    'original_names': [item_name],
                    'in_pantry': pantry_info["available"],
                    'pantry_quantity': pantry_info["quantity"],
                    'pantry_location': pantry_info.get("location", ""),
                    'pantry_item_id': pantry_info.get("pantry_item_id")
                }

        # Process consolidated items and check existing grocery list
        grocery_items_to_insert = []
        updated_items_count = 0
        pantry_sufficient_items = []
        current_time = datetime.now().isoformat()

        for normalized_name, consolidated_item in consolidated_items.items():
            print(f"🔍 Processing: {consolidated_item['item_name']}")

            # If item is sufficiently available in pantry, skip adding to grocery list
            if consolidated_item['in_pantry'] and consolidated_item['pantry_quantity'] >= consolidated_item['quantity']:
                pantry_sufficient_items.append({
                    "name": consolidated_item['item_name'],
                    "needed_quantity": consolidated_item['quantity'],
                    "pantry_quantity": consolidated_item['pantry_quantity'],
                    "location": consolidated_item['pantry_location']
                })
                print(f"✅ {consolidated_item['item_name']} available in pantry - skipping grocery list")
                continue

            # Check if item already exists in grocery list
            existing_item_query = supabase.table("grocery_items") \
                .select("id, quantity, estimated_cost, name") \
                .eq("user_id", req.user_id) \
                .eq("is_purchased", False) \
                .execute()

            existing_item = None
            if existing_item_query.data:
                for existing in existing_item_query.data:
                    existing_normalized = normalize_ingredient_name(existing.get("name", ""))
                    if existing_normalized == normalized_name:
                        existing_item = existing
                        break

            if existing_item:
                # Update existing item
                current_quantity = float(existing_item.get("quantity", "0"))
                current_cost = float(existing_item.get("estimated_cost", 0))

                # Adjust quantity if partially available in pantry
                needed_quantity = consolidated_item['quantity']
                if consolidated_item['in_pantry'] and consolidated_item['pantry_quantity'] > 0:
                    needed_quantity = max(0, needed_quantity - consolidated_item['pantry_quantity'])

                new_quantity = current_quantity + needed_quantity
                new_cost = current_cost + consolidated_item['estimated_cost']

                print(
                    f"🔄 Updating existing: {consolidated_item['item_name']} (qty: {new_quantity}, cost: ${new_cost:.2f})")

                update_result = supabase.table("grocery_items") \
                    .update({
                    "quantity": str(new_quantity),
                    "estimated_cost": round(new_cost, 2),
                    "updated_at": current_time,
                    "in_pantry": consolidated_item['in_pantry'],
                    "pantry_quantity": consolidated_item['pantry_quantity']
                }) \
                    .eq("id", existing_item["id"]) \
                    .execute()

                updated_items_count += 1
            else:
                # Add new item
                needed_quantity = consolidated_item['quantity']
                if consolidated_item['in_pantry'] and consolidated_item['pantry_quantity'] > 0:
                    needed_quantity = max(0, needed_quantity - consolidated_item['pantry_quantity'])

                if needed_quantity > 0:  # Only add if we actually need to buy some
                    item_to_insert = {
                        "user_id": req.user_id,
                        "name": consolidated_item['item_name'],
                        "quantity": str(needed_quantity),
                        "unit": "",
                        "category": consolidated_item['category'],
                        "is_purchased": False,
                        "item_name": consolidated_item['item_name'],
                        "estimated_cost": round(consolidated_item['estimated_cost'], 2),
                        "in_pantry": consolidated_item['in_pantry'],
                        "pantry_quantity": consolidated_item['pantry_quantity'],
                        "created_at": current_time,
                        "updated_at": current_time
                    }

                    grocery_items_to_insert.append(item_to_insert)

        # Insert new items in batch
        inserted_items = []
        if grocery_items_to_insert:
            print(f"➕ Inserting {len(grocery_items_to_insert)} new items")
            insert_result = supabase.table("grocery_items").insert(grocery_items_to_insert).execute()

            if hasattr(insert_result, 'data') and insert_result.data:
                inserted_items = insert_result.data

        total_items_affected = len(inserted_items)
        total_original_items = len(req.grocery_items)
        total_consolidated_items = len(consolidated_items)

        print(f"✅ Grocery list saved: {total_original_items} items → {total_consolidated_items} consolidated")

        return {
            "success": True,
            "message": f"Successfully processed {total_original_items} items into {total_consolidated_items} unique ingredients",
            "inserted_items": total_items_affected,
            "updated_items": updated_items_count,
            "pantry_sufficient": pantry_sufficient_items,
            "total_cost": round(sum(item['estimated_cost'] for item in consolidated_items.values()), 2),
            "consolidation_summary": {
                "original_items": total_original_items,
                "consolidated_items": total_consolidated_items,
                "items_saved": total_original_items - total_consolidated_items,
                "pantry_items_available": len(pantry_sufficient_items)
            }
        }

    except Exception as e:
        print(f"❌ Error in save_grocery_list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save grocery list: {str(e)}")


@router.post("/grocery-list/smart")
async def create_smart_grocery_list(req: SmartGroceryListRequest):
    """Create optimized grocery list with AI substitutions and pantry checking"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Fix: Import from correct path
        try:
            from services.substitution_service import substitution_service
        except ImportError:
            # Fallback if the service isn't available
            print("⚠️ Substitution service not available, continuing without AI substitutions")
            substitution_service = None

        needed_items = []
        pantry_sufficient = []
        substitution_suggestions = []

        # Get user's pantry if checking pantry
        pantry_items = {}
        if req.check_pantry:
            pantry_result = supabase.table("pantry_items") \
                .select("*") \
                .eq("user_id", req.user_id) \
                .execute()

            for item in pantry_result.data or []:
                normalized_name = normalize_ingredient_name(item["name"])
                pantry_items[normalized_name] = item

        # Track items that need substitutions
        missing_ingredients = []

        # Process each recipe ingredient
        for ingredient in req.recipe_ingredients:
            ingredient_name = ingredient.get("name", "")
            needed_quantity = float(ingredient.get("quantity", 1))
            unit = ingredient.get("unit", "")

            normalized_name = normalize_ingredient_name(ingredient_name)

            # Check if we have it in pantry
            if req.check_pantry and normalized_name in pantry_items:
                pantry_item = pantry_items[normalized_name]
                available_quantity = float(pantry_item.get("quantity", 0))

                if available_quantity >= needed_quantity:
                    pantry_sufficient.append({
                        "ingredient": ingredient_name,
                        "needed": needed_quantity,
                        "available": available_quantity,
                        "location": pantry_item.get("location", "Pantry")
                    })
                    continue
                elif available_quantity > 0:
                    # Partial quantity available
                    needed_quantity -= available_quantity

            # Check if ingredient is commonly available or if we should suggest substitutions
            if req.suggest_substitutions:
                # For now, suggest substitutions for expensive or specialty items
                expensive_items = ['saffron', 'truffle', 'wagyu', 'caviar', 'vanilla bean']
                specialty_items = ['miso paste', 'tahini', 'harissa', 'fish sauce', 'coconut cream']

                if any(expensive in ingredient_name.lower() for expensive in expensive_items + specialty_items):
                    missing_ingredients.append(ingredient_name)

            # Add to grocery list
            grocery_item = {
                "user_id": req.user_id,
                "name": ingredient_name,
                "item_name": ingredient_name,
                "quantity": str(needed_quantity),
                "unit": unit,
                "category": ingredient.get("category", "Recipe Generated"),
                "estimated_cost": ingredient.get("estimated_cost", 0),
                "is_purchased": False,
                "in_pantry": normalized_name in pantry_items,
                "pantry_quantity": pantry_items.get(normalized_name, {}).get("quantity", 0),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            needed_items.append(grocery_item)

        # Get AI substitution suggestions for missing/expensive ingredients
        if req.suggest_substitutions and missing_ingredients and substitution_service:
            try:
                ai_substitutions = await substitution_service.get_smart_substitutions(
                    missing_ingredients=missing_ingredients,
                    user_pantry=list(pantry_items.values()) if req.check_pantry else None
                )

                # Add substitution suggestions to grocery items
                for item in needed_items:
                    item_name = item["name"]
                    if item_name in missing_ingredients:
                        # Find substitutions for this item
                        for sub_group in ai_substitutions:
                            if sub_group["original_ingredient"].lower() in item_name.lower():
                                item["suggested_substitutes"] = sub_group["substitutes"][:2]  # Top 2 suggestions
                                break

                substitution_suggestions = ai_substitutions

            except Exception as sub_error:
                print(f"⚠️ Substitution service error: {str(sub_error)}")
                # Continue without substitutions

        # Insert needed items to grocery list
        if needed_items:
            insert_result = supabase.table("grocery_items") \
                .insert(needed_items) \
                .execute()

        return {
            "success": True,
            "items_added": len(needed_items),
            "pantry_sufficient": pantry_sufficient,
            "substitution_suggestions": substitution_suggestions,
            "total_cost": sum(float(item.get("estimated_cost", 0)) for item in needed_items),
            "message": f"Smart grocery list created: {len(needed_items)} items needed, {len(pantry_sufficient)} items available in pantry"
        }

    except Exception as e:
        print(f"❌ Error creating smart grocery list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create smart grocery list: {str(e)}")


# Rest of your existing endpoints remain the same...
@router.get("/grocery-list/{user_id}")
def get_grocery_list(user_id: str, include_purchased: bool = False):
    """Get user's grocery list with enhanced pantry information"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        query = supabase.table("grocery_items") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True)

        if not include_purchased:
            query = query.eq("is_purchased", False)

        result = query.execute()

        grocery_items = result.data or []

        # Enhanced analytics
        total_cost = sum(float(item.get("estimated_cost", 0)) for item in grocery_items)
        items_in_pantry = sum(1 for item in grocery_items if item.get("in_pantry", False))
        potential_savings = sum(
            float(item.get("estimated_cost", 0))
            for item in grocery_items
            if item.get("in_pantry", False) and float(item.get("pantry_quantity", 0)) >= float(item.get("quantity", 0))
        )

        print(f"✅ Retrieved {len(grocery_items)} grocery items for user {user_id}")

        return {
            "grocery_items": grocery_items,
            "total_items": len(grocery_items),
            "total_cost": round(total_cost, 2),
            "analytics": {
                "items_in_pantry": items_in_pantry,
                "potential_savings": round(potential_savings, 2),
                "categories": {},  # Could be calculated
                "substitution_opportunities": sum(1 for item in grocery_items if item.get("suggested_substitutes"))
            }
        }

    except Exception as e:
        print(f"❌ Error in get_grocery_list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get grocery list: {str(e)}")


@router.patch("/grocery-list/{item_id}/purchase")
def mark_item_purchased(item_id: int, user_id: str = Query(...)):
    """Mark grocery item as purchased and optionally add to pantry"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Get the item details first
        item_result = supabase.table("grocery_items") \
            .select("*") \
            .eq("id", item_id) \
            .eq("user_id", user_id) \
            .single() \
            .execute()

        if not item_result.data:
            raise HTTPException(status_code=404, detail="Grocery item not found")

        item = item_result.data

        # Mark as purchased
        result = supabase.table("grocery_items") \
            .update({
            "is_purchased": True,
            "purchased_at": datetime.now().isoformat()
        }) \
            .eq("id", item_id) \
            .eq("user_id", user_id) \
            .execute()

        # Optionally add to pantry (for non-perishables)
        non_perishable_categories = ["Pantry and Staples", "Grains and Carbs", "Frozen and Misc"]
        if item.get("category") in non_perishable_categories:
            try:
                pantry_item = {
                    "user_id": user_id,
                    "name": item.get("name", ""),
                    "category": item.get("category", "Uncategorized"),
                    "quantity": float(item.get("quantity", 1)),
                    "unit": item.get("unit", ""),
                    "cost_per_unit": float(item.get("estimated_cost", 0)) / max(float(item.get("quantity", 1)), 1),
                    "location": "Pantry",
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }

                supabase.table("pantry_items").insert([pantry_item]).execute()
                print(f"📦 Added {item.get('name')} to pantry")

            except Exception as pantry_error:
                print(f"⚠️ Could not add to pantry: {str(pantry_error)}")

        print(f"✅ Marked item {item_id} as purchased for user {user_id}")

        return {"success": True, "message": "Item marked as purchased"}

    except Exception as e:
        print(f"❌ Error in mark_item_purchased: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to mark item as purchased: {str(e)}")


@router.delete("/grocery-list/{item_id}")
def delete_grocery_item(item_id: int, user_id: str = Query(...)):
    """Delete grocery item"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        result = supabase.table("grocery_items") \
            .delete() \
            .eq("id", item_id) \
            .eq("user_id", user_id) \
            .execute()

        print(f"✅ Deleted grocery item {item_id} for user {user_id}")

        return {"success": True, "message": "Item deleted successfully"}

    except Exception as e:
        print(f"❌ Error in delete_grocery_item: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete item: {str(e)}")


@router.delete("/grocery-list/{user_id}/clear-purchased")
def clear_purchased_items(user_id: str):
    """Clear all purchased items"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        result = supabase.table("grocery_items") \
            .delete() \
            .eq("user_id", user_id) \
            .eq("is_purchased", True) \
            .execute()

        print(f"✅ Cleared purchased items for user {user_id}")

        return {"success": True, "message": "Purchased items cleared"}

    except Exception as e:
        print(f"❌ Error in clear_purchased_items: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear purchased items: {str(e)}")


@router.get("/grocery-list/{user_id}/optimized")
def get_optimized_shopping_list(user_id: str):
    """Get shopping list optimized by store layout and shopping preferences"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Get grocery items
        items_result = supabase.table("grocery_items") \
            .select("*") \
            .eq("user_id", user_id) \
            .eq("is_purchased", False) \
            .execute()

        # Get shopping preferences (if table exists)
        try:
            prefs_result = supabase.table("shopping_preferences") \
                .select("*") \
                .eq("user_id", user_id) \
                .execute()
            preferences = prefs_result.data[0] if prefs_result.data else {}
        except:
            preferences = {}

        items = items_result.data or []

        # Default shopping order if no preferences
        default_order = [
            "Produce", "Proteins", "Dairy & Alternatives",
            "Grains and Carbs", "Pantry and Staples", "Frozen and Misc"
        ]

        shopping_order = preferences.get("shopping_order", default_order)

        # Organize items by category in shopping order
        organized_items = {}
        for category in shopping_order:
            organized_items[category] = []

        # Add uncategorized at the end
        organized_items["Other"] = []

        # Sort items into categories
        for item in items:
            category = item.get("category", "Other")
            if category in organized_items:
                organized_items[category].append(item)
            else:
                organized_items["Other"].append(item)

        # Remove empty categories
        organized_items = {k: v for k, v in organized_items.items() if v}

        # Calculate totals
        total_cost = sum(float(item.get("estimated_cost", 0)) for item in items)
        total_items = len(items)

        return {
            "organized_items": organized_items,
            "shopping_order": shopping_order,
            "total_items": total_items,
            "total_cost": round(total_cost, 2),
            "store_name": preferences.get("preferred_store", "Generic Store"),
            "optimization_applied": bool(preferences)
        }

    except Exception as e:
        print(f"❌ Error getting optimized shopping list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get optimized shopping list: {str(e)}")