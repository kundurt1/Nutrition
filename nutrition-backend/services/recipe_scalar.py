# nutrition-backend/services/recipe_scaler.py

import sys
import os
from typing import Dict, List, Optional, Any
import json

# Add the parent directory to sys.path to import from models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import supabase
from services.unit_converter import UnitConverterService


class RecipeScalerService:
    """Service class for recipe scaling operations"""

    def __init__(self):
        self.unit_converter = UnitConverterService()

    async def scale_recipe(self, recipe_name: str, new_servings: int, user_id: str) -> Optional[Dict]:
        """Scale a recipe to new serving size"""
        try:
            if not supabase:
                raise Exception("Database not available")

            # Get the original recipe
            recipe_result = supabase.table("recipes") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("title", recipe_name) \
                .execute()

            if not recipe_result.data:
                return None

            original_recipe = recipe_result.data[0]
            original_servings = 4  # Default if not specified

            # Try to get servings from recipe data or assume from context
            if 'servings' in original_recipe:
                original_servings = original_recipe['servings']

            # Calculate scaling factor
            scaling_factor = new_servings / original_servings

            # Scale ingredients
            ingredients = original_recipe.get('ingredients', [])
            scaled_ingredients = []

            for ingredient in ingredients:
                scaled_ingredient = {
                    'name': ingredient.get('name', ''),
                    'quantity': float(ingredient.get('quantity', 0)) * scaling_factor,
                    'unit': ingredient.get('unit', ''),
                    'cost_per_unit': float(ingredient.get('cost_per_unit', 0)),
                    'category': ingredient.get('category', 'other')
                }
                scaled_ingredients.append(scaled_ingredient)

            # Create scaled recipe response
            scaled_recipe = {
                'name': f"{original_recipe['title']} (for {new_servings} servings)",
                'original_servings': new_servings,
                'ingredients': scaled_ingredients,
                'instructions': original_recipe.get('directions', []),
                'prep_time': original_recipe.get('prep_time', 0),
                'cook_time': original_recipe.get('cook_time', 0),
                'cuisine': original_recipe.get('cuisine', ''),
                'difficulty': original_recipe.get('difficulty', 'medium'),
                'tags': original_recipe.get('tags', [])
            }

            return {
                'recipe': scaled_recipe,
                'scaling_factor': scaling_factor,
                'original_servings': original_servings,
                'new_servings': new_servings
            }

        except Exception as e:
            print(f"Error scaling recipe: {e}")
            return None

    async def convert_recipe_units(self, recipe_name: str, unit_conversions: Dict[str, str], user_id: str) -> bool:
        """Convert ingredients in a recipe to different units"""
        try:
            if not supabase:
                return False

            # Get the recipe
            recipe_result = supabase.table("recipes") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("title", recipe_name) \
                .execute()

            if not recipe_result.data:
                return False

            recipe = recipe_result.data[0]
            ingredients = recipe.get('ingredients', [])

            # Convert units for specified ingredients
            updated_ingredients = []
            for ingredient in ingredients:
                ingredient_name = ingredient.get('name', '').lower()

                # Check if this ingredient should be converted
                new_unit = None
                for conv_name, conv_unit in unit_conversions.items():
                    if conv_name.lower() in ingredient_name:
                        new_unit = conv_unit
                        break

                if new_unit:
                    # Convert the unit
                    old_quantity = float(ingredient.get('quantity', 0))
                    old_unit = ingredient.get('unit', '')

                    converted_quantity = self.unit_converter.convert_units(old_quantity, old_unit, new_unit)

                    if converted_quantity is not None:
                        # Update ingredient with new unit and quantity
                        ingredient['quantity'] = converted_quantity
                        ingredient['unit'] = new_unit

                        # Adjust cost per unit
                        if 'cost_per_unit' in ingredient and ingredient['cost_per_unit'] > 0:
                            conversion_factor = converted_quantity / old_quantity if old_quantity > 0 else 1
                            ingredient['cost_per_unit'] = ingredient['cost_per_unit'] / conversion_factor

                updated_ingredients.append(ingredient)

            # Update the recipe in database
            update_result = supabase.table("recipes") \
                .update({"ingredients": updated_ingredients}) \
                .eq("id", recipe["id"]) \
                .execute()

            return len(update_result.data) > 0

        except Exception as e:
            print(f"Error converting recipe units: {e}")
            return False

    async def get_grocery_list(self, recipe_name: str, servings: int, user_id: str,
                               preferred_units: Optional[Dict[str, str]] = None) -> Optional[Dict]:
        """Generate grocery list for a scaled recipe"""
        try:
            # First scale the recipe
            scaled_result = await self.scale_recipe(recipe_name, servings, user_id)
            if not scaled_result:
                return None

            scaled_recipe = scaled_result['recipe']
            grocery_list = []
            total_cost = 0

            for ingredient in scaled_recipe['ingredients']:
                # Apply unit conversion if preferred unit is specified
                display_ingredient = ingredient.copy()

                if preferred_units and ingredient['name'] in preferred_units:
                    new_unit = preferred_units[ingredient['name']]
                    converted_quantity = self.unit_converter.convert_units(
                        ingredient['quantity'],
                        ingredient['unit'],
                        new_unit
                    )

                    if converted_quantity is not None:
                        conversion_factor = converted_quantity / ingredient['quantity'] if ingredient[
                                                                                               'quantity'] > 0 else 1
                        display_ingredient.update({
                            'quantity': converted_quantity,
                            'unit': new_unit,
                            'cost_per_unit': ingredient[
                                                 'cost_per_unit'] / conversion_factor if conversion_factor != 0 else
                            ingredient['cost_per_unit']
                        })

                # Calculate total cost for this ingredient
                item_total_cost = display_ingredient['quantity'] * display_ingredient['cost_per_unit']
                total_cost += item_total_cost

                grocery_item = {
                    'name': display_ingredient['name'],
                    'quantity': round(display_ingredient['quantity'], 2),
                    'unit': display_ingredient['unit'],
                    'category': display_ingredient.get('category', 'other'),
                    'cost_per_unit': display_ingredient['cost_per_unit'],
                    'total_cost': round(item_total_cost, 2),
                    'compatible_units': self.unit_converter.get_compatible_units(display_ingredient['unit'])
                }
                grocery_list.append(grocery_item)

            # Sort by category for organized shopping
            grocery_list.sort(key=lambda x: (x['category'], x['name']))

            return {
                'grocery_list': grocery_list,
                'total_cost': round(total_cost, 2),
                'total_items': len(grocery_list),
                'servings': servings
            }

        except Exception as e:
            print(f"Error generating grocery list: {e}")
            return None

    async def get_combined_grocery_list(self, recipe_servings: Dict[str, int], user_id: str,
                                        preferred_units: Optional[Dict[str, str]] = None) -> Dict:
        """Generate combined grocery list for multiple recipes"""
        try:
            combined_ingredients = {}
            total_cost = 0

            for recipe_name, servings in recipe_servings.items():
                grocery_result = await self.get_grocery_list(recipe_name, servings, user_id, preferred_units)

                if grocery_result:
                    for item in grocery_result['grocery_list']:
                        key = (item['name'], item['unit'])

                        if key in combined_ingredients:
                            # Combine quantities and costs
                            combined_ingredients[key]['quantity'] += item['quantity']
                            combined_ingredients[key]['total_cost'] += item['total_cost']
                        else:
                            combined_ingredients[key] = item.copy()

            # Convert back to list and calculate total
            combined_list = []
            for item in combined_ingredients.values():
                item['quantity'] = round(item['quantity'], 2)
                item['total_cost'] = round(item['total_cost'], 2)
                total_cost += item['total_cost']
                combined_list.append(item)

            # Sort by category and name
            combined_list.sort(key=lambda x: (x['category'], x['name']))

            return {
                'grocery_list': combined_list,
                'total_cost': round(total_cost, 2),
                'total_items': len(combined_list),
                'servings': sum(recipe_servings.values())
            }

        except Exception as e:
            print(f"Error generating combined grocery list: {e}")
            return {
                'grocery_list': [],
                'total_cost': 0,
                'total_items': 0,
                'servings': 0
            }

    async def get_nutrition_comparison(self, recipe_name: str, serving_sizes: List[int], user_id: str) -> Optional[
        Dict]:
        """Compare nutrition across different serving sizes"""
        try:
            if not supabase:
                return None

            # Get the original recipe
            recipe_result = supabase.table("recipes") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("title", recipe_name) \
                .execute()

            if not recipe_result.data:
                return None

            original_recipe = recipe_result.data[0]
            macro_estimate = original_recipe.get('macro_estimate', {})
            original_servings = 4  # Default

            comparisons = {}

            for serving_size in serving_sizes:
                scaling_factor = serving_size / original_servings

                # Scale nutrition values
                scaled_nutrition_per_serving = {}
                scaled_nutrition_total = {}

                for macro, value in macro_estimate.items():
                    if isinstance(value, (int, float)):
                        scaled_total = value * scaling_factor
                        scaled_per_serving = scaled_total / serving_size if serving_size > 0 else 0
                    else:
                        # Handle string values like "25g"
                        numeric_value = float(''.join(filter(str.isdigit, str(value)))) if str(value) else 0
                        scaled_total = numeric_value * scaling_factor
                        scaled_per_serving = scaled_total / serving_size if serving_size > 0 else 0

                    scaled_nutrition_per_serving[macro] = round(scaled_per_serving, 1)
                    scaled_nutrition_total[macro] = round(scaled_total, 1)

                # Calculate cost
                cost_estimate = float(original_recipe.get('cost_estimate', 0))
                total_cost = cost_estimate * scaling_factor
                cost_per_serving = total_cost / serving_size if serving_size > 0 else 0

                comparisons[f"{serving_size}_servings"] = {
                    'total_servings': serving_size,
                    'per_serving': scaled_nutrition_per_serving,
                    'total_recipe': scaled_nutrition_total,
                    'total_cost': round(total_cost, 2),
                    'cost_per_serving': round(cost_per_serving, 2)
                }

            return {
                'comparisons': comparisons,
                'recipe_name': recipe_name
            }

        except Exception as e:
            print(f"Error comparing nutrition: {e}")
            return None

    async def optimize_serving_size(self, recipe_name: str, target_calories_per_serving: float, user_id: str) -> \
    Optional[int]:
        """Find optimal serving size to meet target calories per serving"""
        try:
            if not supabase:
                return None

            # Get the original recipe
            recipe_result = supabase.table("recipes") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("title", recipe_name) \
                .execute()

            if not recipe_result.data:
                return None

            original_recipe = recipe_result.data[0]
            macro_estimate = original_recipe.get('macro_estimate', {})

            # Get total calories for original recipe
            total_calories = macro_estimate.get('calories', 0)
            if isinstance(total_calories, str):
                total_calories = float(''.join(filter(str.isdigit, total_calories))) if total_calories else 0

            if total_calories <= 0:
                return None

            # Calculate required servings to meet target calories
            required_servings = total_calories / target_calories_per_serving

            # Round to nearest whole number
            return max(1, round(required_servings))

        except Exception as e:
            print(f"Error optimizing serving size: {e}")
            return None

    async def batch_scale_recipes(self, recipe_names: List[str], new_servings: int, user_id: str) -> Dict[str, Any]:
        """Scale multiple recipes at once"""
        try:
            scaled_recipes = {}

            for recipe_name in recipe_names:
                scaled_result = await self.scale_recipe(recipe_name, new_servings, user_id)
                if scaled_result:
                    scaled_recipes[recipe_name] = scaled_result

            return scaled_recipes

        except Exception as e:
            print(f"Error batch scaling recipes: {e}")
            return {}

    async def import_recipe(self, recipe_data: Dict[str, Any], user_id: str, save_to_db: bool = True) -> bool:
        """Import a recipe from data"""
        try:
            if not save_to_db or not supabase:
                return True  # Just validate the data

            # Convert recipe data to our database format
            recipe_insert = {
                "user_id": user_id,
                "title": recipe_data.get('name', 'Imported Recipe'),
                "ingredients": recipe_data.get('ingredients', []),
                "directions": recipe_data.get('instructions', []),
                "tags": recipe_data.get('tags', []),
                "cuisine": recipe_data.get('cuisine', ''),
                "macro_estimate": {
                    "calories": recipe_data.get('nutrition', {}).get('calories', 0),
                    "protein": recipe_data.get('nutrition', {}).get('protein', 0),
                    "carbs": recipe_data.get('nutrition', {}).get('carbs', 0),
                    "fat": recipe_data.get('nutrition', {}).get('fat', 0),
                    "fiber": recipe_data.get('nutrition', {}).get('fiber', 0)
                },
                "cost_estimate": recipe_data.get('cost_estimate', 0),
                "prep_time": recipe_data.get('prep_time', 0),
                "cook_time": recipe_data.get('cook_time', 0),
                "difficulty": recipe_data.get('difficulty', 'medium')
            }

            insert_result = supabase.table("recipes").insert(recipe_insert).execute()

            return len(insert_result.data) > 0

        except Exception as e:
            print(f"Error importing recipe: {e}")
            return False

    async def export_recipe(self, recipe_name: str, user_id: str, format: str = "json") -> Optional[Dict]:
        """Export a recipe"""
        try:
            if not supabase:
                return None

            # Get the recipe
            recipe_result = supabase.table("recipes") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("title", recipe_name) \
                .execute()

            if not recipe_result.data:
                return None

            recipe = recipe_result.data[0]

            # Format for export
            export_data = {
                'name': recipe['title'],
                'servings': 4,  # Default
                'ingredients': recipe.get('ingredients', []),
                'instructions': recipe.get('directions', []),
                'prep_time': recipe.get('prep_time', 0),
                'cook_time': recipe.get('cook_time', 0),
                'cuisine': recipe.get('cuisine', ''),
                'difficulty': recipe.get('difficulty', 'medium'),
                'tags': recipe.get('tags', []),
                'nutrition': recipe.get('macro_estimate', {}),
                'cost_estimate': recipe.get('cost_estimate', 0),
                'created_date': recipe.get('created_at', '')
            }

            return {
                'recipe_data': export_data,
                'format': format,
                'exported_at': supabase.table("recipes").select("created_at").execute().data[0][
                    'created_at'] if supabase.table("recipes").select("created_at").execute().data else None
            }

        except Exception as e:
            print(f"Error exporting recipe: {e}")
            return None

    async def search_recipes(self, user_id: str, query: str = "", cuisine: str = None, difficulty: str = None,
                             tag: str = None, max_cook_time: int = None) -> List[Dict]:
        """Search recipes with filters"""
        try:
            if not supabase:
                return []

            # Start with basic query
            query_builder = supabase.table("recipes") \
                .select(
                "id, title, cuisine, difficulty, prep_time, cook_time, tags, cost_estimate, macro_estimate, created_at") \
                .eq("user_id", user_id)

            # Apply filters
            if cuisine:
                query_builder = query_builder.eq("cuisine", cuisine)

            if difficulty:
                query_builder = query_builder.eq("difficulty", difficulty)

            # Execute query
            result = query_builder.order("created_at", desc=True).execute()

            recipes = result.data or []

            # Apply additional filters in Python (since Supabase has limited filtering)
            if query:
                query_lower = query.lower()
                recipes = [r for r in recipes if query_lower in r['title'].lower()]

            if tag:
                recipes = [r for r in recipes if tag in r.get('tags', [])]

            if max_cook_time:
                recipes = [r for r in recipes if r.get('cook_time', 0) <= max_cook_time]

            # Format for response
            formatted_recipes = []
            for recipe in recipes:
                formatted_recipe = {
                    'id': recipe['id'],
                    'name': recipe['title'],
                    'cuisine': recipe['cuisine'],
                    'difficulty': recipe['difficulty'],
                    'prep_time': recipe.get('prep_time', 0),
                    'cook_time': recipe.get('cook_time', 0),
                    'total_time': recipe.get('prep_time', 0) + recipe.get('cook_time', 0),
                    'tags': recipe.get('tags', []),
                    'cost_estimate': recipe.get('cost_estimate', 0),
                    'calories': recipe.get('macro_estimate', {}).get('calories', 0),
                    'created_at': recipe.get('created_at', '')
                }
                formatted_recipes.append(formatted_recipe)

            return formatted_recipes

        except Exception as e:
            print(f"Error searching recipes: {e}")
            return []

    async def get_recipe_analytics(self, recipe_name: str, user_id: str) -> Optional[Dict]:
        """Get comprehensive analytics for a recipe"""
        try:
            if not supabase:
                return None

            # Get the recipe
            recipe_result = supabase.table("recipes") \
                .select("*") \
                .eq("user_id", user_id) \
                .eq("title", recipe_name) \
                .execute()

            if not recipe_result.data:
                return None

            recipe = recipe_result.data[0]
            ingredients = recipe.get('ingredients', [])
            macro_estimate = recipe.get('macro_estimate', {})

            # Calculate cost analysis
            total_cost = float(recipe.get('cost_estimate', 0))
            servings = 4  # Default
            cost_per_serving = total_cost / servings if servings > 0 else 0

            # Cost by category
            cost_by_category = {}
            for ingredient in ingredients:
                category = ingredient.get('category', 'other')
                ingredient_cost = float(ingredient.get('quantity', 0)) * float(ingredient.get('cost_per_unit', 0))
                cost_by_category[category] = cost_by_category.get(category, 0) + ingredient_cost

            # Nutrition analysis
            calories = macro_estimate.get('calories', 0)
            if isinstance(calories, str):
                calories = float(''.join(filter(str.isdigit, calories))) if calories else 0

            protein = macro_estimate.get('protein', 0)
            if isinstance(protein, str):
                protein = float(''.join(filter(str.isdigit, str(protein)))) if protein else 0

            carbs = macro_estimate.get('carbs', 0)
            if isinstance(carbs, str):
                carbs = float(''.join(filter(str.isdigit, str(carbs)))) if carbs else 0

            fat = macro_estimate.get('fat', 0)
            if isinstance(fat, str):
                fat = float(''.join(filter(str.isdigit, str(fat)))) if fat else 0

            fiber = macro_estimate.get('fiber', 0)
            if isinstance(fiber, str):
                fiber = float(''.join(filter(str.isdigit, str(fiber)))) if fiber else 0

            # Macronutrient percentages
            total_macro_calories = (protein * 4) + (carbs * 4) + (fat * 9)
            macro_percentages = {}
            if total_macro_calories > 0:
                macro_percentages = {
                    'protein_percent': round((protein * 4 / total_macro_calories) * 100, 1),
                    'carbs_percent': round((carbs * 4 / total_macro_calories) * 100, 1),
                    'fat_percent': round((fat * 9 / total_macro_calories) * 100, 1)
                }

            # Get ingredient categories
            ingredient_categories = list(set(ing.get('category', 'other') for ing in ingredients))

            return {
                'recipe_name': recipe['title'],
                'servings': servings,
                'total_time': recipe.get('prep_time', 0) + recipe.get('cook_time', 0),
                'cost_analysis': {
                    'total_cost': round(total_cost, 2),
                    'cost_per_serving': round(cost_per_serving, 2),
                    'cost_by_category': {k: round(v, 2) for k, v in cost_by_category.items()}
                },
                'nutrition_per_serving': {
                    'calories': round(calories / servings, 1) if servings > 0 else 0,
                    'protein': round(protein / servings, 1) if servings > 0 else 0,
                    'carbs': round(carbs / servings, 1) if servings > 0 else 0,
                    'fat': round(fat / servings, 1) if servings > 0 else 0,
                    'fiber': round(fiber / servings, 1) if servings > 0 else 0
                },
                'total_nutrition': {
                    'calories': round(calories, 1),
                    'protein': round(protein, 1),
                    'carbs': round(carbs, 1),
                    'fat': round(fat, 1),
                    'fiber': round(fiber, 1)
                },
                'macro_percentages': macro_percentages,
                'ingredient_categories': ingredient_categories,
                'ingredient_count': len(ingredients),
                'cost_per_calorie': round(cost_per_serving / (calories / servings),
                                          4) if calories > 0 and servings > 0 else 0
            }

        except Exception as e:
            print(f"Error getting recipe analytics: {e}")
            return None

    async def get_user_recipes(self, user_id: str) -> List[Dict]:
        """Get all recipes for a user"""
        try:
            return await self.search_recipes(user_id)
        except Exception as e:
            print(f"Error getting user recipes: {e}")
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
            print(f"Error deleting recipe: {e}")
            return False