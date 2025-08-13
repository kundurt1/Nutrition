# nutrition-backend/services/recipe_scaler.py

from typing import Dict, List, Optional, Any
import re
import json
from services.unit_converter import UnitConverterService

# Import supabase from your database module
try:
    from database import supabase
except ImportError:
    try:
        from db import supabase
    except ImportError:
        supabase = None
        print("⚠️ Warning: Could not import supabase")


def _normalize_ingredient_row(row):
    """Normalize ingredient data to consistent format"""
    if isinstance(row, str):
        return {
            "name": row,
            "quantity": None,
            "unit": None,
            "cost_per_unit": None
        }

    if isinstance(row, dict):
        return {
            "name": row.get("name", ""),
            "quantity": row.get("quantity"),
            "unit": row.get("unit"),
            "cost_per_unit": row.get("cost_per_unit")
        }

    return {
        "name": str(row),
        "quantity": None,
        "unit": None,
        "cost_per_unit": None
    }


class RecipeScalerService:
    def __init__(self):
        self.unit_converter = UnitConverterService()
        print("✅ RecipeScalerService initialized")

    async def _get_recipe_for_user(self, recipe_name: str, user_id: str) -> Optional[Dict]:
        """Fetch recipe from database for user - FIXED to only query existing columns"""
        try:
            print(f"🔍 Looking for recipe: '{recipe_name}' for user: {user_id}")

            if not supabase:
                print("❌ Supabase client not available")
                return None

            # First, let's see what recipes this user has (only query 'title' column that exists)
            print(f"📚 Checking what recipes user {user_id} has...")
            all_recipes = supabase.table("recipes") \
                .select("id, title") \
                .eq("user_id", user_id) \
                .execute()

            if all_recipes.data:
                print(f"📚 User has {len(all_recipes.data)} recipes:")
                for r in all_recipes.data[:5]:  # Show first 5
                    print(f"  - ID: {r.get('id')}, Title: '{r.get('title')}'")
            else:
                print("❌ User has no recipes in database")
                return None

            # Try exact match on title field
            print(f"🔍 Trying exact match on 'title' field for: '{recipe_name}'")
            result = supabase.table("recipes") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("title", recipe_name) \
                .execute()

            if result.data and len(result.data) > 0:
                print(f"✅ Found recipe by exact title match")
                return result.data[0]

            # Try case-insensitive match on title
            print(f"🔍 Trying case-insensitive match on 'title' field...")
            result = supabase.table("recipes") \
                .select("*") \
                .eq("user_id", user_id) \
                .ilike("title", recipe_name) \
                .execute()

            if result.data and len(result.data) > 0:
                print(f"✅ Found recipe by case-insensitive title match")
                return result.data[0]

            # Try partial match on title (contains the search term)
            print(f"🔍 Trying partial match on 'title' field...")
            result = supabase.table("recipes") \
                .select("*") \
                .eq("user_id", user_id) \
                .ilike("title", f"%{recipe_name}%") \
                .execute()

            if result.data and len(result.data) > 0:
                print(f"✅ Found recipe by partial title match: '{result.data[0].get('title')}'")
                return result.data[0]

            # Try searching for any word from the recipe name
            words = recipe_name.split()
            if len(words) > 1:
                print(f"🔍 Trying to match any word from: {words}")
                for word in words:
                    if len(word) > 3:  # Skip short words
                        result = supabase.table("recipes") \
                            .select("*") \
                            .eq("user_id", user_id) \
                            .ilike("title", f"%{word}%") \
                            .execute()

                        if result.data and len(result.data) > 0:
                            print(f"✅ Found recipe by word '{word}': '{result.data[0].get('title')}'")
                            return result.data[0]

            print(f"❌ Recipe '{recipe_name}' not found for user {user_id}")
            if all_recipes.data:
                print(f"💡 Available recipes for this user:")
                for r in all_recipes.data[:10]:  # Show up to 10
                    print(f"    - '{r.get('title')}'")

            return None

        except Exception as e:
            print(f"❌ Error fetching recipe: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_time_to_minutes(self, time_str: Any) -> int:
        """Parse time string to minutes"""
        if not time_str:
            return 30

        if isinstance(time_str, (int, float)):
            return int(time_str)

        if isinstance(time_str, str):
            time_str = time_str.lower()

            if 'hour' in time_str:
                hours = re.findall(r'(\d+(?:\.\d+)?)\s*(?:hour|hr)', time_str)
                if hours:
                    return int(float(hours[0]) * 60)

            if 'min' in time_str:
                minutes = re.findall(r'(\d+(?:\.\d+)?)\s*(?:minute|min)', time_str)
                if minutes:
                    return int(float(minutes[0]))

            # Try to extract just numbers
            numbers = re.findall(r'(\d+(?:\.\d+)?)', time_str)
            if numbers:
                return int(float(numbers[0]))

        return 30

    async def scale_recipe(self, recipe_name: str, new_servings: int, user_id: str):
        """Scale a recipe to different servings with all required return fields"""
        print(f"\n🔧 Starting recipe scaling...")
        print(f"   Recipe: '{recipe_name}'")
        print(f"   New servings: {new_servings}")
        print(f"   User ID: {user_id}")

        # Fetch recipe from database
        original = await self._get_recipe_for_user(recipe_name, user_id)
        if not original:
            print("❌ Recipe not found, returning None")
            return None

        print(f"✅ Recipe found: {original.get('title')}")

        # Determine original servings
        original_servings = original.get("servings") or original.get("original_servings") or 4
        print(f"📊 Original servings: {original_servings}")

        # Calculate scaling factor
        scaling_factor = new_servings / original_servings if original_servings else 1.0
        print(f"📊 Scaling factor: {scaling_factor}")

        # Process ingredients
        raw_ingredients = original.get("ingredients", [])

        # Handle both string and JSON formats
        if isinstance(raw_ingredients, str):
            try:
                raw_ingredients = json.loads(raw_ingredients)
                print(f"✅ Parsed ingredients from JSON string")
            except:
                print(f"⚠️ Could not parse ingredients JSON, using empty list")
                raw_ingredients = []

        print(f"📦 Processing {len(raw_ingredients)} ingredients...")

        # Scale ingredients
        scaled_ingredients = []
        for i, row in enumerate(raw_ingredients):
            item = _normalize_ingredient_row(row)
            # Scale only numeric quantities
            if item["quantity"] is not None:
                try:
                    original_qty = float(item["quantity"])
                    scaled_qty = round(original_qty * scaling_factor, 2)
                    item["quantity"] = scaled_qty
                    print(f"   - {item['name']}: {original_qty} -> {scaled_qty} {item.get('unit', '')}")
                except (ValueError, TypeError):
                    print(f"   - {item['name']}: Could not scale quantity")
            scaled_ingredients.append(item)

        # Scale cost
        original_cost = original.get("cost_estimate") or original.get("cost") or 0
        try:
            scaled_cost = float(original_cost) * scaling_factor
            print(f"💰 Cost: ${original_cost} -> ${scaled_cost:.2f}")
        except (ValueError, TypeError):
            scaled_cost = 0.0
            print(f"⚠️ Could not scale cost")

        # Parse macros if they're in string format
        macros = original.get("macros") or original.get("macro_estimate")
        if isinstance(macros, str):
            try:
                macros = json.loads(macros)
                print(f"✅ Parsed macros from JSON string")
            except:
                macros = {}
                print(f"⚠️ Could not parse macros JSON")

        # Parse directions if they're in string format
        directions = original.get("directions", [])
        if isinstance(directions, str):
            try:
                directions = json.loads(directions)
            except:
                directions = []

        # Build the recipe object
        recipe = {
            "recipe_name": original.get("title") or original.get("recipe_name") or recipe_name,
            "title": original.get("title") or original.get("recipe_name") or recipe_name,
            "ingredients": scaled_ingredients,
            "directions": directions,
            "servings": new_servings,
            "original_servings": original_servings,
            "cost_estimate": round(scaled_cost, 2),
            "macros": macros,
            "cuisine": original.get("cuisine"),
            "difficulty": original.get("difficulty"),
            "prep_time": original.get("prep_time"),
            "cook_time": original.get("cook_time"),
            "tags": original.get("tags", [])
        }

        # Return with all required fields for ScaledRecipeResponse
        result = {
            "recipe": recipe,
            "scaling_factor": round(scaling_factor, 2),
            "original_servings": original_servings,
            "new_servings": new_servings
        }

        print(f"✅ Recipe scaling complete!")
        print(f"📊 Returning scaled recipe with {len(scaled_ingredients)} ingredients")

        return result

    async def convert_recipe_units(self, recipe_name: str, unit_conversions: Dict[str, str], user_id: str) -> bool:
        """Convert ingredients in a recipe to different units"""
        try:
            if not supabase:
                raise Exception("Database not available")

            # Get the recipe using our helper method
            recipe = await self._get_recipe_for_user(recipe_name, user_id)
            if not recipe:
                return False

            ingredients = recipe.get('ingredients', [])

            # Handle string format
            if isinstance(ingredients, str):
                try:
                    ingredients = json.loads(ingredients)
                except:
                    return False

            # Convert units for specified ingredients
            updated_ingredients = []
            for ingredient in ingredients:
                ingredient = _normalize_ingredient_row(ingredient)
                ingredient_name = ingredient.get('name', '').lower()

                # Check if this ingredient needs unit conversion
                target_unit = None
                for ingredient_key, unit in unit_conversions.items():
                    if ingredient_key.lower() in ingredient_name:
                        target_unit = unit
                        break

                if target_unit and ingredient.get('quantity'):
                    # Perform unit conversion
                    conversion_result = self.unit_converter.convert_units(
                        float(ingredient.get('quantity', 0)),
                        ingredient.get('unit', ''),
                        target_unit
                    )

                    if conversion_result['conversion_successful']:
                        ingredient['quantity'] = conversion_result['converted_quantity']
                        ingredient['unit'] = target_unit

                updated_ingredients.append(ingredient)

            # Update the recipe in database
            update_data = {'ingredients': json.dumps(updated_ingredients)}

            result = supabase.table("recipes") \
                .update(update_data) \
                .eq("user_id", user_id) \
                .eq("title", recipe.get("title")) \
                .execute()

            return len(result.data) > 0

        except Exception as e:
            print(f"❌ Error converting recipe units: {str(e)}")
            return False

    # Include the other methods (get_grocery_list, optimize_serving_size, etc.) from before...
    # I'll just include the key ones for brevity

    async def get_grocery_list(self, recipe_name: str, servings: int, user_id: str,
                               preferred_units: Dict[str, str] = None) -> Optional[Dict]:
        """Generate grocery list for a scaled recipe"""
        try:
            # First scale the recipe
            scaled_recipe_result = await self.scale_recipe(recipe_name, servings, user_id)
            if not scaled_recipe_result:
                return None

            scaled_recipe = scaled_recipe_result['recipe']
            ingredients = scaled_recipe.get('ingredients', [])

            # Build grocery list
            grocery_list = []
            total_cost = 0

            for ingredient in ingredients:
                item = {
                    'name': ingredient.get('name', ''),
                    'quantity': ingredient.get('quantity', 0),
                    'unit': ingredient.get('unit', ''),
                    'cost': (ingredient.get('quantity', 0) or 0) * (ingredient.get('cost_per_unit', 0) or 0)
                }

                # Apply preferred units if specified
                if preferred_units and item['name'] in preferred_units:
                    target_unit = preferred_units[item['name']]
                    conversion = self.unit_converter.convert_units(
                        item['quantity'],
                        item['unit'],
                        target_unit
                    )
                    if conversion['conversion_successful']:
                        item['quantity'] = conversion['converted_quantity']
                        item['unit'] = target_unit

                grocery_list.append(item)
                total_cost += item['cost']

            return {
                'grocery_list': grocery_list,
                'total_cost': round(total_cost, 2),
                'total_items': len(grocery_list),
                'servings': servings
            }

        except Exception as e:
            print(f"❌ Error generating grocery list: {str(e)}")
            return None

    # Add stub methods for other operations referenced in the router
    async def get_nutrition_comparison(self, recipe_name: str, serving_sizes: List[int], user_id: str):
        """Stub for nutrition comparison"""
        print(f"⚠️ get_nutrition_comparison not fully implemented")
        return {"comparisons": {}, "recipe_name": recipe_name}

    async def optimize_serving_size(self, recipe_name: str, target_calories: int, user_id: str):
        """Stub for optimize serving size"""
        print(f"⚠️ optimize_serving_size not fully implemented")
        return 4  # Default servings

    async def batch_scale_recipes(self, recipe_names: List[str], new_servings: int, user_id: str):
        """Stub for batch scaling"""
        print(f"⚠️ batch_scale_recipes not fully implemented")
        return []

    async def import_recipe(self, recipe_data: Dict, user_id: str, save_to_db: bool):
        """Stub for import recipe"""
        print(f"⚠️ import_recipe not fully implemented")
        return True

    async def export_recipe(self, recipe_name: str, user_id: str, format: str):
        """Stub for export recipe"""
        print(f"⚠️ export_recipe not fully implemented")
        return {"recipe_name": recipe_name, "format": format}

    async def search_recipes(self, user_id: str, query: str = "", cuisine: str = "",
                             difficulty: str = "", tag: str = "", max_cook_time: int = None):
        """Stub for search recipes"""
        print(f"⚠️ search_recipes not fully implemented")
        return []

    async def get_recipe_analytics(self, recipe_name: str, user_id: str):
        """Stub for recipe analytics"""
        print(f"⚠️ get_recipe_analytics not fully implemented")
        return None

    async def get_user_recipes(self, user_id: str):
        """Get all recipes for a user"""
        try:
            if not supabase:
                return []

            result = supabase.table("recipes") \
                .select("*") \
                .eq("user_id", user_id) \
                .execute()

            return result.data or []
        except Exception as e:
            print(f"❌ Error getting user recipes: {str(e)}")
            return []

    async def delete_recipe(self, recipe_name: str, user_id: str):
        """Delete a recipe"""
        try:
            if not supabase:
                return False

            result = supabase.table("recipes") \
                .delete() \
                .eq("user_id", user_id) \
                .eq("title", recipe_name) \
                .execute()

            return len(result.data) > 0
        except Exception as e:
            print(f"❌ Error deleting recipe: {str(e)}")
            return False