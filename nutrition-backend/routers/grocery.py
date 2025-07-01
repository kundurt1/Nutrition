from fastapi import APIRouter, HTTPException, Query
from models.groceryModels import SaveGroceryListRequest
from database import supabase
from datetime import datetime
import re
from typing import Dict, List

router = APIRouter()

def normalize_ingredient_name(name: str) -> str:
    """Normalize ingredient names to consolidate similar items."""
    if not name:
        return 'unknown'

    normalized = name.lower().strip()

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
    return normalized if normalized else name.lower()

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

@router.post("/save-grocery-list")
def save_grocery_list(req: SaveGroceryListRequest):
    """Save consolidated grocery list - used by GenerateRecipe.jsx and GroceryList.jsx"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        if not req.user_id:
            raise HTTPException(status_code=400, detail="User ID is required")

        if not req.grocery_items or len(req.grocery_items) == 0:
            raise HTTPException(status_code=400, detail="No grocery items provided")

        print(f"Processing {len(req.grocery_items)} grocery items for user {req.user_id}")

        # First, consolidate the incoming items
        consolidated_items = {}
        for item in req.grocery_items:
            normalized_name = normalize_ingredient_name(item.item_name)

            if normalized_name in consolidated_items:
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

        # Process consolidated items
        grocery_items_to_insert = []
        updated_items_count = 0
        current_time = datetime.now().isoformat()

        for normalized_name, consolidated_item in consolidated_items.items():
            print(f"Processing: {consolidated_item['item_name']}")

            # Check if item already exists
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

                new_quantity = current_quantity + consolidated_item['quantity']
                new_cost = current_cost + consolidated_item['estimated_cost']

                print(f"Updating existing: {consolidated_item['item_name']} (qty: {new_quantity}, cost: ${new_cost:.2f})")

                update_result = supabase.table("grocery_items") \
                    .update({
                        "quantity": str(new_quantity),
                        "estimated_cost": round(new_cost, 2),
                        "updated_at": current_time
                    }) \
                    .eq("id", existing_item["id"]) \
                    .execute()

                updated_items_count += 1
            else:
                # Add new item
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

                grocery_items_to_insert.append(item_to_insert)

        # Insert new items in batch
        inserted_items = []
        if grocery_items_to_insert:
            print(f"Inserting {len(grocery_items_to_insert)} new items")
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
            "total_cost": round(sum(item['estimated_cost'] for item in consolidated_items.values()), 2),
            "consolidation_summary": {
                "original_items": total_original_items,
                "consolidated_items": total_consolidated_items,
                "items_saved": total_original_items - total_consolidated_items
            }
        }

    except Exception as e:
        print(f"❌ Error in save_grocery_list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save grocery list: {str(e)}")

@router.get("/grocery-list/{user_id}")
def get_grocery_list(user_id: str, include_purchased: bool = False):
    """Get user's grocery list - used by GroceryList.jsx"""
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
        total_cost = sum(float(item.get("estimated_cost", 0)) for item in grocery_items)

        print(f"✅ Retrieved {len(grocery_items)} grocery items for user {user_id}")

        return {
            "grocery_items": grocery_items,
            "total_items": len(grocery_items),
            "total_cost": round(total_cost, 2)
        }

    except Exception as e:
        print(f"❌ Error in get_grocery_list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get grocery list: {str(e)}")

@router.patch("/grocery-list/{item_id}/purchase")
def mark_item_purchased(item_id: int, user_id: str = Query(...)):
    """Mark grocery item as purchased - used by GroceryList.jsx"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

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

        print(f"✅ Marked item {item_id} as purchased for user {user_id}")

        return {"success": True, "message": "Item marked as purchased"}

    except Exception as e:
        print(f"❌ Error in mark_item_purchased: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to mark item as purchased: {str(e)}")

# Additional endpoint to delete items
@router.delete("/grocery-list/{item_id}")
def delete_grocery_item(item_id: int, user_id: str = Query(...)):
    """Delete grocery item - used by GroceryList.jsx"""
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

# Endpoint to clear all purchased items
@router.delete("/grocery-list/{user_id}/clear-purchased")
def clear_purchased_items(user_id: str):
    """Clear all purchased items - used by GroceryList.jsx"""
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