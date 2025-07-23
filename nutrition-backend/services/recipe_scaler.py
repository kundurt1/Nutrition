# services/recipe_scaler.py - Final fixed version

import sys
import os
from typing import Dict, List, Optional, Any
import json
import re

# Add the parent directory to sys.path to import from models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import supabase
from services.unit_converter import UnitConverterService


class RecipeScalerService:
    """Service class for recipe scaling operations"""

    def __init__(self):
        self.unit_converter = UnitConverterService()

    def parse_time_to_minutes(self, time_value) -> int:
        """Parse time strings to integer minutes"""
        if isinstance(time_value, int):
            return time_value

        if isinstance(time_value, str):
            # Handle empty strings
            if not time_value.strip():
                return 30  # Default to 30 minutes for empty values

            # Remove extra spaces and convert to lowercase
            time_str = time_value.strip().lower()

            # Try to extract numbers from strings like "15 minutes", "1 hour", etc.
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

        # Default fallback
        return 30  # Default to 30 minutes

    async def scale_recipe(self, recipe_name: str, new_servings: int, user_id: str) -> Optional[Dict]:
        """Scale a recipe to new serving size"""
        try:
            if not supabase:
                raise Exception("Database not available")

            print(f"🔍 Scaling recipe '{recipe_name}' to {new_servings} servings for user {user_id}")

            # Get the original recipe - fix the SQL query
            recipe_result = supabase.table("recipes") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("title", recipe_name) \
                .execute()

            if not recipe_result.data:
                print(f"❌ Recipe '{recipe_name}' not found for user {user_id}")
                return None

            original_recipe = recipe_result.data[0]
            print(f"✅ Found recipe: {original_recipe.get('title', original_recipe.get('recipe_name', 'Unknown'))}")

            # Get original servings - check multiple possible fields
            original_servings = 4  # Default

            for field in ['servings', 'original_servings', 'serves']:
                if field in original_recipe and original_recipe[field]:
                    try:
                        original_servings = int(original_recipe[field])
                        break
                    except (ValueError, TypeError):
                        continue

            print(f"📊 Original servings: {original_servings}, New servings: {new_servings}")

            # Calculate scaling factor
            scaling_factor = new_servings / original_servings
            print(f"⚖️ Scaling factor: {scaling_factor}")

            # Scale ingredients
            ingredients = original_recipe.get('ingredients', [])
            scaled_ingredients = []

            print(f"🥄 Scaling {len(ingredients)} ingredients:")
            for i, ingredient in enumerate(ingredients):
                try:
                    original_quantity = float(ingredient.get('quantity', 0))
                    scaled_quantity = original_quantity * scaling_factor

                    scaled_ingredient = {
                        'name': ingredient.get('name', ''),
                        'quantity': round(scaled_quantity, 2),
                        'unit': ingredient.get('unit', ''),
                        'cost_per_unit': float(ingredient.get('cost_per_unit', 0)),
                        'category': ingredient.get('category', 'other')
                    }
                    scaled_ingredients.append(scaled_ingredient)
                    print(
                        f"  {i + 1}. {ingredient.get('name', 'ingredient')}: {original_quantity} → {scaled_quantity} {ingredient.get('unit', '')}")

                except (ValueError, TypeError) as e:
                    print(f"⚠️ Error scaling ingredient {ingredient.get('name', 'unknown')}: {e}")
                    # Still scale it but with original quantity if parsing fails
                    scaled_ingredient = {
                        'name': ingredient.get('name', ''),
                        'quantity': ingredient.get('quantity', 0),  # Keep original
                        'unit': ingredient.get('unit', ''),
                        'cost_per_unit': float(ingredient.get('cost_per_unit', 0)),
                        'category': ingredient.get('category', 'other')
                    }
                    scaled_ingredients.append(scaled_ingredient)

            # Parse and scale nutrition if available
            scaled_nutrition = {}
            original_macros = original_recipe.get('macros', {})

            if original_macros:
                try:
                    # Scale calories
                    original_calories = 0
                    if 'calories' in original_macros:
                        try:
                            original_calories = int(float(str(original_macros['calories']).replace('cal', '')))
                        except (ValueError, TypeError):
                            original_calories = 0

                    scaled_nutrition['calories'] = int(original_calories * scaling_factor)

                    # Scale other macros
                    for macro in ['protein', 'carbs', 'fat', 'fiber']:
                        if macro in original_macros:
                            try:
                                # Extract number from strings like "25g" or "25"
                                macro_str = str(original_macros[macro])
                                number = re.findall(r'(\d+(?:\.\d+)?)', macro_str)
                                if number:
                                    original_value = float(number[0])
                                    scaled_value = original_value * scaling_factor
                                    scaled_nutrition[macro] = f"{scaled_value:.1f}g"
                                else:
                                    scaled_nutrition[macro] = original_macros[macro]
                            except (ValueError, TypeError):
                                scaled_nutrition[macro] = original_macros[macro]

                    print(f"🍎 Scaled nutrition: {scaled_nutrition}")

                except Exception as e:
                    print(f"⚠️ Error scaling nutrition: {e}")
                    scaled_nutrition = original_macros

            # Parse time values to integers (minutes) - with better handling
            prep_time = self.parse_time_to_minutes(original_recipe.get('prep_time', ''))
            cook_time = self.parse_time_to_minutes(original_recipe.get('cook_time', ''))

            print(f"⏰ Times - Prep: {prep_time}min, Cook: {cook_time}min")

            # Scale cost estimate
            original_cost = 0
            try:
                original_cost = float(original_recipe.get('cost_estimate', 0))
            except (ValueError, TypeError):
                original_cost = 0

            scaled_cost = original_cost * scaling_factor
            print(f"💰 Cost: ${original_cost:.2f} → ${scaled_cost:.2f}")

            # Create scaled recipe response
            scaled_recipe = {
                'name': f"{original_recipe.get('title', original_recipe.get('recipe_name', 'Recipe'))} (for {new_servings} servings)",
                'original_servings': new_servings,
                'ingredients': scaled_ingredients,
                'instructions': original_recipe.get('directions', original_recipe.get('instructions', [])),
                'prep_time': prep_time,  # Now guaranteed to be integer
                'cook_time': cook_time,  # Now guaranteed to be integer
                'cuisine': original_recipe.get('cuisine', ''),
                'difficulty': original_recipe.get('difficulty', 'medium'),
                'tags': original_recipe.get('tags', []),
                'macros': scaled_nutrition,
                'cost_estimate': round(scaled_cost, 2)
            }

            response = {
                'recipe': scaled_recipe,
                'scaling_factor': scaling_factor,
                'original_servings': original_servings,
                'new_servings': new_servings
            }

            print(f"✅ Successfully scaled recipe with factor {scaling_factor}")
            return response

        except Exception as e:
            print(f"❌ Error scaling recipe: {str(e)}")
            import traceback
            traceback.print_exc()
            raise e

    async def convert_recipe_units(self, recipe_name: str, unit_conversions: Dict[str, str], user_id: str) -> bool:
        """Convert ingredients in a recipe to different units"""
        try:
            if not supabase:
                raise Exception("Database not available")

            # Get the recipe - try both title and recipe_name fields
            recipe_result = supabase.table("recipes") \
                .select("*") \
                .eq("user_id", user_id) \
                .or_(f"title.eq.{recipe_name},recipe_name.eq.{recipe_name}") \
                .execute()

            if not recipe_result.data:
                return False

            recipe = recipe_result.data[0]
            ingredients = recipe.get('ingredients', [])

            # Convert units for specified ingredients
            updated_ingredients = []
            for ingredient in ingredients:
                ingredient_name = ingredient.get('name', '').lower()

                # Check if this ingredient needs unit conversion
                target_unit = None
                for ingredient_key, unit in unit_conversions.items():
                    if ingredient_key.lower() in ingredient_name:
                        target_unit = unit
                        break

                if target_unit:
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
            update_data = {'ingredients': updated_ingredients}
            supabase.table("recipes") \
                .update(update_data) \
                .eq("user_id", user_id) \
                .eq("title", recipe_name) \
                .execute()

            return True

        except Exception as e:
            print(f"❌ Error converting recipe units: {str(e)}")
            return False

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

            grocery_items = []
            total_cost = 0

            for ingredient in ingredients:
                try:
                    quantity = float(ingredient.get('quantity', 0))
                    cost_per_unit = float(ingredient.get('cost_per_unit', 0))
                    estimated_cost = quantity * cost_per_unit

                    item = {
                        'name': ingredient.get('name', ''),
                        'quantity': quantity,
                        'unit': ingredient.get('unit', ''),
                        'estimated_cost': round(estimated_cost, 2),
                        'category': ingredient.get('category', 'other')
                    }

                    total_cost += estimated_cost
                    grocery_items.append(item)

                except (ValueError, TypeError):
                    # Skip ingredients with invalid data
                    continue

            return {
                'grocery_list': grocery_items,
                'total_cost': round(total_cost, 2),
                'total_items': len(grocery_items),
                'servings': servings
            }

        except Exception as e:
            print(f"❌ Error generating grocery list: {str(e)}")
            return None

    async def get_nutrition_comparison(self, recipe_name: str, serving_sizes: List[int], user_id: str) -> Optional[
        Dict]:
        """Compare nutrition across different serving sizes"""
        try:
            comparisons = {}

            for servings in serving_sizes:
                scaled_result = await self.scale_recipe(recipe_name, servings, user_id)
                if scaled_result:
                    scaled_recipe = scaled_result['recipe']
                    macros = scaled_recipe.get('macros', {})

                    # Calculate per-serving nutrition
                    per_serving = {}
                    if macros:
                        try:
                            total_calories = int(macros.get('calories', 0))
                            per_serving = {
                                'calories': total_calories // servings if total_calories else 0,
                                'protein': f"{float(str(macros.get('protein', '0')).replace('g', '')) / servings:.1f}g" if macros.get(
                                    'protein') else "0g",
                                'carbs': f"{float(str(macros.get('carbs', '0')).replace('g', '')) / servings:.1f}g" if macros.get(
                                    'carbs') else "0g",
                                'fat': f"{float(str(macros.get('fat', '0')).replace('g', '')) / servings:.1f}g" if macros.get(
                                    'fat') else "0g"
                            }
                        except (ValueError, TypeError):
                            per_serving = {}

                    comparisons[f"{servings}_servings"] = {
                        'total_nutrition': macros,
                        'per_serving_nutrition': per_serving,
                        'total_cost': scaled_recipe.get('cost_estimate', 0),
                        'cost_per_serving': round(scaled_recipe.get('cost_estimate', 0) / servings,
                                                  2) if servings > 0 else 0
                    }

            return {
                'comparisons': comparisons,
                'recipe_name': recipe_name
            }

        except Exception as e:
            print(f"❌ Error comparing nutrition: {str(e)}")
            return None

    async def optimize_serving_size(self, recipe_name: str, target_calories_per_serving: int, user_id: str) -> Optional[
        int]:
        """Find optimal serving size to meet target calories"""
        try:
            # Get base recipe (4 servings)
            base_result = await self.scale_recipe(recipe_name, 4, user_id)
            if not base_result:
                return None

            base_recipe = base_result['recipe']
            base_macros = base_recipe.get('macros', {})

            if not base_macros or not base_macros.get('calories'):
                return None

            try:
                total_calories = int(base_macros.get('calories', 0))
            except (ValueError, TypeError):
                return None

            # Calculate optimal servings
            optimal_servings = max(1, round(total_calories / target_calories_per_serving))

            return optimal_servings

        except Exception as e:
            print(f"❌ Error optimizing serving size: {str(e)}")
            return None

    async def get_user_recipes(self, user_id: str) -> List[Dict]:
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

    async def delete_recipe(self, recipe_name: str, user_id: str) -> bool:
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

    # Additional helper methods
    async def batch_scale_recipes(self, recipe_names: List[str], new_servings: int, user_id: str) -> List[Dict]:
        """Scale multiple recipes at once"""
        results = []

        for recipe_name in recipe_names:
            try:
                result = await self.scale_recipe(recipe_name, new_servings, user_id)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"❌ Error scaling recipe {recipe_name}: {str(e)}")
                continue

        return results

    async def get_combined_grocery_list(self, recipe_servings: Dict[str, int], user_id: str,
                                        preferred_units: Dict[str, str] = None) -> Dict:
        """Generate combined grocery list for multiple recipes"""
        try:
            combined_items = {}
            total_cost = 0

            for recipe_name, servings in recipe_servings.items():
                grocery_result = await self.get_grocery_list(recipe_name, servings, user_id, preferred_units)

                if grocery_result:
                    for item in grocery_result['grocery_list']:
                        item_name = item['name'].lower()

                        if item_name in combined_items:
                            # Combine quantities if same unit
                            if combined_items[item_name]['unit'] == item['unit']:
                                combined_items[item_name]['quantity'] += item['quantity']
                                combined_items[item_name]['estimated_cost'] += item['estimated_cost']
                            else:
                                # Different units, keep separate
                                combined_items[f"{item_name}_{item['unit']}"] = item
                        else:
                            combined_items[item_name] = item

                    total_cost += grocery_result['total_cost']

            return {
                'grocery_list': list(combined_items.values()),
                'total_cost': round(total_cost, 2),
                'total_items': len(combined_items),
                'servings': sum(recipe_servings.values())
            }

        except Exception as e:
            print(f"❌ Error generating combined grocery list: {str(e)}")
            return {
                'grocery_list': [],
                'total_cost': 0,
                'total_items': 0,
                'servings': 0
            }